document.addEventListener('DOMContentLoaded', () => {
    // ... your existing enforceRoleBasedAccess() routine invocation ...

    // Locate the unique structural Sign Out node handle
    const signOutBtn = document.getElementById('signOutBtn');

    if (signOutBtn) {
        signOutBtn.addEventListener('click', (e) => {
            // 1. Terminate native structural link jumping behaviors safely
            e.preventDefault();

            localStorage.clear();
            sessionStorage.clear(); 

            window.location.href = "/sign-in.html"; 
        });
    }
});