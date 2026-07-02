import { initCharts } from './charts.js';
import { initMap } from './map.js';

document.addEventListener("DOMContentLoaded", () => {
    
    // Tab Switching Logic
    const navItems = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            // Remove active class from all nav items and tabs
            navItems.forEach(nav => nav.classList.remove('active'));
            tabContents.forEach(tab => tab.classList.remove('active'));

            // Add active class to clicked nav item
            item.classList.add('active');

            // Show corresponding tab content
            const targetId = item.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');

            // Initialize content if needed
            if (targetId === 'tab-generation') {
                initCharts();
            } else if (targetId === 'tab-maps') {
                initMap();
            }
        });
    });

    // Initialize the default tab
    initCharts();
});