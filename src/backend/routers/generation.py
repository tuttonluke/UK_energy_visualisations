import httpx
import time
import asyncio
from datetime import datetime, timedelta
import urllib.parse
from fastapi import APIRouter

router = APIRouter()

GENERATION_CACHE = None
LAST_FETCH_TIME = 0
CACHE_TTL = 300  # 5 minutes

async def fetch_pvlive_data(client, min_dt, max_dt):
    # PVLive is queried by end time of the period.
    # BMRS start times range from min_dt to max_dt.
    # So we need PVLive from min_dt to max_dt + 30 mins.
    start_str = min_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_dt = max_dt + timedelta(minutes=60)
    end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    url = f"https://api.pvlive.uk/pvlive/api/v4/pes/0?start={start_str}&end={end_str}"
    try:
        res = await client.get(url, timeout=10.0)
        res.raise_for_status()
        data = res.json()
        
        pv_dict = {}
        for row in data.get('data', []):
            # row[1] is datetime_gmt (end of period)
            # row[2] is generation_mw
            pv_dict[row[1]] = row[2]
        return pv_dict
    except Exception as e:
        print(f"PVLive fetch failed: {e}")
        return {}

async def fetch_neso_embedded_wind(client, min_date):
    # Fetch from both the live dataset and the current archive (H2 2026) to be safe
    datasets = [
        "db6c038f-98af-4570-ab60-24d71ebd0ae5", # Live
        "31861619-0b86-47ba-bac2-d008a760af54"  # Archive 2026 H2
    ]
    
    date_str = min_date.strftime("%Y-%m-%d")
    neso_dict = {}
    
    for dataset_id in datasets:
        sql = f'SELECT "DATE_GMT", "TIME_GMT", "EMBEDDED_WIND_FORECAST" FROM "{dataset_id}" WHERE "DATE_GMT" >= \'{date_str}\' LIMIT 2000'
        url = f'https://api.neso.energy/api/3/action/datastore_search_sql?sql={urllib.parse.quote(sql)}'
        
        try:
            res = await client.get(url, timeout=10.0)
            if res.status_code == 200:
                data = res.json()
                for row in data.get('result', {}).get('records', []):
                    d_str = row['DATE_GMT'].split('T')[0]
                    t_str = row['TIME_GMT']
                    if t_str == '24:00':
                        t_str = '00:00'
                        dt = datetime.fromisoformat(f"{d_str}T{t_str}+00:00") + timedelta(days=1)
                    else:
                        if len(t_str) == 4:
                            t_str = '0' + t_str
                        dt = datetime.fromisoformat(f"{d_str}T{t_str}:00+00:00")
                    
                    dt_iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                    # If there are multiple forecasts for the same period, we just take the latest one we parse
                    neso_dict[dt_iso] = row['EMBEDDED_WIND_FORECAST']
        except Exception as e:
            print(f"NESO fetch failed for {dataset_id}: {e}")
            
    return neso_dict

async def fetch_generation_summary():
    global GENERATION_CACHE, LAST_FETCH_TIME
    
    if time.time() - LAST_FETCH_TIME < CACHE_TTL and GENERATION_CACHE:
        return GENERATION_CACHE
        
    print("Cache expired. Fetching fresh data...")
    url_bmrs = "https://data.elexon.co.uk/bmrs/api/v1/generation/outturn/summary"
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Fetch BMRS Data
            response = await client.get(url_bmrs, timeout=10.0)
            response.raise_for_status()
            bmrs_data = response.json()
            
            if not bmrs_data:
                return {"data": []}
                
            # 2. Determine time bounds
            times = [datetime.fromisoformat(d['startTime'].replace('Z', '+00:00')) for d in bmrs_data]
            min_dt = min(times)
            max_dt = max(times)
            
            # 3. Fetch PVLive and NESO concurrently
            pv_task = fetch_pvlive_data(client, min_dt, max_dt)
            neso_task = fetch_neso_embedded_wind(client, min_dt)
            
            pv_dict, neso_dict = await asyncio.gather(pv_task, neso_task)
            
            # 4. Merge data
            for period in bmrs_data:
                start_dt = datetime.fromisoformat(period['startTime'].replace('Z', '+00:00'))
                end_dt = start_dt + timedelta(minutes=30)
                end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                
                # PVLive solar outturn
                solar_gen = pv_dict.get(end_iso, 0)
                if solar_gen > 0:
                    # Find existing SOLAR to group them, or just add if we group in frontend
                    # Wait, BMRS has 'SOLAR' and 'WIND'. Let's find them and add to them directly.
                    solar_found = False
                    for item in period['data']:
                        if item['fuelType'] == 'SOLAR':
                            item['generation'] += solar_gen
                            solar_found = True
                            break
                    if not solar_found:
                        period['data'].append({'fuelType': 'SOLAR', 'generation': solar_gen})
                        
                # NESO embedded wind forecast
                wind_gen = neso_dict.get(end_iso, 0)
                if wind_gen > 0:
                    wind_found = False
                    for item in period['data']:
                        if item['fuelType'] == 'WIND':
                            item['generation'] += wind_gen
                            wind_found = True
                            break
                    if not wind_found:
                        period['data'].append({'fuelType': 'WIND', 'generation': wind_gen})
            
            GENERATION_CACHE = bmrs_data
            LAST_FETCH_TIME = time.time()
            print("Live generation data cached successfully (including embedded).")
        except Exception as e:
            print(f"Failed to fetch generation data: {e}")
            if GENERATION_CACHE:
                return GENERATION_CACHE
            return {"data": []}
            
    return GENERATION_CACHE

@router.get("/summary")
async def get_generation_summary():
    return await fetch_generation_summary()
