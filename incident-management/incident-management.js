import { initializeFirebase } from '/lib/firebase_init.js';

document.addEventListener('DOMContentLoaded', async () => {
    const tableBody = document.getElementById('recordsTableBody');

    // KPI Indicators Element Bindings
    const kpiSos = document.getElementById('kpiActiveSos');
    const kpiAccidents = document.getElementById('kpiAccidents');
    const kpiRoadblocks = document.getElementById('kpiRoadblocks');
    const kpiResolved = document.getElementById('kpiResolved');

    function formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';
        if (typeof timestamp.toDate === 'function') {
            return timestamp.toDate().toLocaleString('en-MY', { timeZone: 'Asia/Kuala_Lumpur' });
        }
        return String(timestamp);
    }

    try {
        // Shared dynamic platform initialization hook
        const { db } = await initializeFirebase();

        // Setup live data synchronizer using onSnapshot mapping
        db.collection("emergencyAlert").onSnapshot((snapshot) => {
            let rowsHtml = "";

            // Dynamic count evaluation from real-time snapshot arrays
            let counterSos = 0;
            let counterAccident = 0;
            let counterRoadblock = 0;
            let counterResolved = 0;

            snapshot.forEach((doc) => {
                const data = doc.data();
                const type = String(data.type || '').toLowerCase();
                const status = String(data.status || '').toLowerCase();

                if (status === 'resolved' || status === 'closed') {
                    counterResolved++;
                } else {
                    if (type === 'sos') counterSos++;
                    if (type === 'accident') counterAccident++;
                    if (type === 'roadblock') counterRoadblock++;
                }
            });

            // Update KPI numerical displays dynamically from computed values
            kpiSos.textContent = counterSos;
            kpiAccidents.textContent = counterAccident;
            kpiRoadblocks.textContent = counterRoadblock;
            kpiResolved.textContent = counterResolved;

            if (snapshot.empty) {
                tableBody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted"><i class="bi bi-check-circle text-success me-1"></i> No incident reports detected on highway networks.</td></tr>`;
                return;
            }

            // Record parsing rendering pipeline logic loop
            snapshot.forEach((doc) => {
                const item = doc.data();

                // Dynamic Priority badge rendering
                let priorityBadge = `<span class="badge bg-secondary">LOW</span>`;
                const p = String(item.priority || '').toUpperCase();
                if (p === 'HIGH') priorityBadge = `<span class="badge bg-danger">HIGH</span>`;
                if (p === 'MED' || p === 'MEDIUM') priorityBadge = `<span class="badge bg-warning text-dark">MED</span>`;

                // Dynamic Operational status badge evaluation 
                let statusBadge = `<span class="badge bg-secondary">${item.status || 'Active'}</span>`;
                const s = String(item.status || '').toLowerCase();
                if (s === 'active' || s === 'critical') statusBadge = `<span class="badge bg-danger px-2.5 py-1.5 border">Active</span>`;
                if (s === 'dispatching' || s === 'in progress') statusBadge = `<span class="badge bg-warning text-dark px-2.5 py-1.5 border">In Progress</span>`;
                if (s === 'resolved' || s === 'closed') statusBadge = `<span class="badge bg-success px-2.5 py-1.5 border">Resolved</span>`;

                // Mapped variables strictly depend on data schemas (no structural hardcoding)
                rowsHtml += `
                    <tr>
                        <td class="text-secondary small fw-bold">${item.emergencyAlertID || doc.id}</td>
                        <td><span class="badge bg-dark font-monospace px-2 py-1">${item.type || 'Incident'}</span></td>
                        <td>${priorityBadge}</td>
                        <td class="fw-semibold text-dark"><i class="bi bi-geo-alt-fill text-muted me-1"></i>${item.location || 'Expressway (Main)'}</td>
                        <td class="text-muted small">${formatTimestamp(item.createdAt)}</td>
                        <td>${statusBadge}</td>
                    </tr>
                `;
            });

            tableBody.innerHTML = rowsHtml;

        }, (error) => {
            console.error("Firestore Streaming Loop Failed: ", error);
        });

    } catch (err) {
        console.error("Initialization error:", err);
        tableBody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-danger"><i class="bi bi-exclamation-octagon-fill me-1"></i> Firebase Integration Error: ${err.message}</td></tr>`;
    }
});


/**
 * Incident Management Center - Dynamic Layout Rendering Engine
 */

// Cache DOM target containers (Removed connectionStatusBtn safely)
const elements = {
    kpiActiveSos: document.getElementById('kpiActiveSos'),
    kpiCongestion: document.getElementById('kpiCongestion'),
    kpiAccidents: document.getElementById('kpiAccidents'),
    kpiWeather: document.getElementById('kpiWeather'),
    kpiRoadblocks: document.getElementById('kpiRoadblocks'),
    kpiResolved: document.getElementById('kpiResolved'),
    emergencyTableBody: document.getElementById('emergencyTableBody'),
    trafficTableBody: document.getElementById('trafficTableBody'),
    timelineContainer: document.getElementById('timelineContainer'),
    filterPriority: document.getElementById('filterPriority'),
    filterTypes: document.querySelectorAll('.filter-type')
};

// Application Global State variables
let incidentDataState = {
    emergencyAlerts: [],
    congestionAlerts: [],
    trafficFlows: [],
    weatherSnapshots: []
};

/**
 * Priority Badge Component Generator
 */
function getPriorityBadgeHTML(priority) {
    const p = String(priority).toUpperCase();
    if (p === 'HIGH') return `<span class="badge bg-danger">HIGH</span>`;
    if (p === 'MED') return `<span class="badge bg-warning text-dark">MED</span>`;
    if (p === 'LOW') return `<span class="badge bg-info text-dark">LOW</span>`;
    return `<span class="badge bg-secondary">${p || 'UNKNOWN'}</span>`;
}

/**
 * Status Badge Component Generator
 */
function getStatusBadgeHTML(status) {
    const s = String(status).toLowerCase();
    if (s === 'critical' || s === 'active') return `<span class="badge bg-danger">${status}</span>`;
    if (s === 'dispatching' || s === 'in progress') return `<span class="badge bg-warning text-dark">${status}</span>`;
    if (s === 'resolved' || s === 'closed') return `<span class="badge bg-success">${status}</span>`;
    return `<span class="badge bg-secondary">${status || 'Pending'}</span>`;
}

/**
 * Dynamic KPI Card Counter Refresh Logic
 */
function renderKPIs(metrics) {
    elements.kpiActiveSos.textContent = metrics.activeSos ?? 0;
    elements.kpiCongestion.textContent = metrics.congestion ?? 0;
    elements.kpiAccidents.textContent = metrics.accidents ?? 0;
    elements.kpiWeather.textContent = metrics.weatherAlerts ?? 0;
    elements.kpiRoadblocks.textContent = metrics.roadblocks ?? 0;
    elements.kpiResolved.textContent = metrics.resolved ?? 0;
}

/**
 * Dynamic Emergency Table Row Insertion Matrix
 */
function renderEmergencyTable(alerts) {
    if (!alerts || alerts.length === 0) {
        elements.emergencyTableBody.innerHTML = `
            <tr><td colspan="5" class="text-center text-muted py-4">No critical emergency items found.</td></tr>`;
        return;
    }

    elements.emergencyTableBody.innerHTML = alerts.map(alert => `
        <tr>
            <td><strong>${alert.emergencyAlertID || ''}</strong></td>
            <td><span class="badge bg-dark">${alert.type || ''}</span></td>
            <td>${getPriorityBadgeHTML(alert.priority)}</td>
            <td>${alert.location || 'Unknown Coordinates'}</td>
            <td>${getStatusBadgeHTML(alert.status)}</td>
        </tr>
    `).join('');
}

/**
 * Dynamic Traffic Table Row Insertion Matrix
 */
function renderTrafficTable(alerts) {
    if (!alerts || alerts.length === 0) {
        elements.trafficTableBody.innerHTML = `
            <tr><td colspan="5" class="text-center text-muted py-4">No congestion anomalies registered.</td></tr>`;
        return;
    }

    elements.trafficTableBody.innerHTML = alerts.map(alert => `
        <tr>
            <td><strong>${alert.congestionAlertID || ''}</strong></td>
            <td>${alert.type || 'Traffic'}</td>
            <td>${getPriorityBadgeHTML(alert.priority)}</td>
            <td>${alert.tollLocationID || 'Main Express Section'}</td>
            <td><span class="fw-bold text-dark">${alert.level || 'NORMAL'} Volume</span></td>
        </tr>
    `).join('');
}

/**
 * Timeline Log Row Insertion Components
 */
function renderTimeline(events) {
    if (!events || events.length === 0) {
        elements.timelineContainer.innerHTML = `<li class="list-group-item text-center text-muted py-3">No historical snapshots to show.</li>`;
        return;
    }

    elements.timelineContainer.innerHTML = events.map(evt => `
        <li class="list-group-item d-flex justify-content-between align-items-center">
            <div>
                <i class="${evt.iconClass || 'bi bi-info-circle-fill'} me-2 text-primary"></i>
                <strong>${evt.timeString || ''}</strong> - ${evt.description || ''}
            </div>
            <span class="text-muted small">${evt.relativeTime || ''}</span>
        </li>
    `).join('');
}

/**
 * Hook this function execution up to your WebSocket connection, 
 * MQTT streaming Client, or Firebase Firestore `onSnapshot()` listeners.
 */
function updateDashboardState(incomingData) {
    // 1. Assign values to active state variables
    incidentDataState = { ...incidentDataState, ...incomingData };
    
    // 2. Perform table structural interface mapping injections
    renderKPIs(incomingData.metrics || {});
    renderEmergencyTable(incidentDataState.emergencyAlerts);
    renderTrafficTable(incidentDataState.congestionAlerts);
    renderTimeline(incomingData.timelineEvents || []);
}

// Global Filter UI Event Listeners hooks Setup
elements.filterPriority.addEventListener('change', (e) => {
    console.log(`Filtering data tracking views by: ${e.target.value}`);
});

elements.filterTypes.forEach(checkbox => {
    checkbox.addEventListener('change', () => {
        const activeTypes = Array.from(elements.filterTypes).filter(i => i.checked).map(i => i.value);
        console.log("Active rendering classifications selected:", activeTypes);
    });
});