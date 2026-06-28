document.addEventListener('DOMContentLoaded', () => {
    // ... your existing enforceRoleBasedAccess() routine invocation ...

    // Locate the unique structural Sign Out node handle
    const signOutBtn = document.getElementById('signOutBtn');

    if (signOutBtn) {
        signOutBtn.addEventListener('click', (e) => {
            // 1. Terminate native structural link jumping behaviors safely
            e.preventDefault();

            // 2. Clear out all position tracking keys inside the active Session Engine
            sessionStorage.clear(); 
            // sessionStorage.removeItem('positionID');
            // sessionStorage.removeItem('loginUser');
            // alert("Session cleared");

            window.location.href = "/sign-in.html"; 
        });
    }
});