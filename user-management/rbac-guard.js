/**
 * PLUS HIGHWAYS — Master Role-Based Access Control (RBAC) System Guard
 * Position IDs: 
 * - PID00001: Web Administrator
 * - PID00002: Highway Patrol Officer
 * - PID00003: Manager
 */

// 1. Centralized Master Access Matrix mapping file paths to allowed Position IDs
const RBAC_MATRIX = {
    "user-management.html": ["PID00003"],
    "toll-rates.html": ["PID00001", "PID00003"],
    "license-plate-entry-exit.html": ["PID00001", "PID00002", "PID00003"],
    "cctv-streaming.html": ["PID00001", "PID00002", "PID00003"],
    "weather-data.html": ["PID00001", "PID00002", "PID00003"],
    "incident-management.html": ["PID00001", "PID00002", "PID00003"],
    "vehicle-verifications.html": ["PID00001", "PID00003"],
    "revenue-management.html": ["PID00001", "PID00003"],
    "inquiry-reply.html": ["PID00001", "PID00002", "PID00003"],
    "profile-info.html": ["PID00001", "PID00002", "PID00003"]
};

// 2. Sidebar Navigation Trimming Engine
function enforceSidebarLinks(currentRoleID) {
    const sidebarItems = document.querySelectorAll('#sidebar .nav-item[data-roles]');
    console.log(`[RBAC] Filtering ${sidebarItems.length} sidebar items for ${currentRoleID}`);

    sidebarItems.forEach(item => {
        const allowedRolesAttr = item.getAttribute('data-roles');
        if (!allowedRolesAttr) return;

        const allowedRoles = allowedRolesAttr.split(',').map(id => id.trim().toUpperCase());

        // Physically strip out unauthorized navigation menus from DOM
        if (!allowedRoles.includes(currentRoleID)) {
            item.remove();
        }
    });
}

// 3. Master Page Guard Logic Engine
function checkPageAuthorization() {
    let currentRoleID = localStorage.getItem('positionID');
    let localFullName = localStorage.getItem('fullName');
    let localStaffID = localStorage.getItem('staffID');
    // let currentRoleID = sessionStorage.getItem('positionID');
    
    // Extract current clean file name from location path (e.g., "user-management.html")
    const fullPath = window.location.pathname;
    const currentPageFile = fullPath.substring(fullPath.lastIndexOf('/') + 1);

    console.log(`[RBAC Execution] Page: ${currentPageFile} | Loaded Session:`, currentRoleID);

    // Explicitly check for completely unrestricted, public authorization entry gates
    const publicPages = ["sign-in.html"];
    if (publicPages.includes(currentPageFile.toLowerCase())) {
        console.log(`[RBAC] Public asset access granted for: ${currentPageFile}`);
        return; // Exit early and allow normal execution
    }

    // STRICT BLANK SESSION CHECK: If session is null, empty, or undefined on a protected page
    if (!currentRoleID || currentRoleID.trim() === "") {
        console.error(`[RBAC Violation] No valid identity found for a protected resource.`);
        triggerAccessDeniedScreen();
        return;
    }

    // Standardize identity formatting
    currentRoleID = currentRoleID.trim().toUpperCase();

    // Look up what roles are allowed on this specific asset page file
    const allowedRolesForThisPage = RBAC_MATRIX[currentPageFile];

    // If the page isn't registered in our matrix map, protect by default and lock out
    if (!allowedRolesForThisPage) {
        console.warn(`[RBAC Warning] ${currentPageFile} is unmapped. Catch-all security lockout activated.`);
        triggerAccessDeniedScreen();
        return;
    }

    // Validate active session against allowed permissions profile matrix
    if (!allowedRolesForThisPage.includes(currentRoleID)) {
        console.error(`[RBAC Violation] Unauthorized access signature for page ${currentPageFile}`);
        triggerAccessDeniedScreen();
        return;
    }

    // Pass Verification: Safe to cleanly filter out remaining UI view modules
    enforceSidebarLinks(currentRoleID);
}

// Helper utility to render full screen security block and redirect to entry gate
function triggerAccessDeniedScreen() {
    // Wipe structural body elements completely to eliminate data leak vectors
    document.body.innerHTML = `
        <div class="container d-flex justify-content-center align-items-center" style="height: 100vh; font-family: sans-serif; background-color: #f8f9fa;">
            <div class="text-center" style="max-width: 500px; padding: 40px 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 8px; background: #fff;">
                <h1 style="color: #dc3545; margin-bottom: 15px; font-size: 2.5rem;">403 - Access Denied</h1>
                <p style="color: #6c757d; font-size: 16px; margin-bottom: 25px;">You must be logged in with appropriate administrative clearance to view this page.</p>
                <p style="font-size: 14px; color: #0d6efd; font-weight: bold;">Returning to secure terminal portal...</p>
            </div>
        </div>`;
    
    // Evict user back to your landing login gateway
    setTimeout(() => {
        window.location.href = "/sign-in.html"; 
    }, 2000);
}

// 4. Runtime Lifecycle Initialization Trigger
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkPageAuthorization);
} else {
    checkPageAuthorization();
}

// 4. Runtime Lifecycle Initialization Trigger
function initApp() {
    // A. Run your security block first
    checkPageAuthorization();

    // B. Safely bind your UI elements now that the DOM is guaranteed to be ready
    const loginUser = document.getElementById("profile-name");
    
    // Fetch the individual pieces from session storage
    const localFullName = localStorage.getItem("fullName");
    const localStaffID = localStorage.getItem("loginUser");

    // Verify the UI element exists and we have at least the full name
    if (loginUser && localFullName) {
        if (localStaffID) {
            // Formats exactly to: Full Name (ID12345)
            loginUser.textContent = `${localFullName} (${localStaffID})`;
        } else {
            // Fallback if staffID isn't found for some reason
            loginUser.textContent = localFullName;
        }
    }
}

// Kick off the application based on the browser state
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}