(() => {
    const page = document.documentElement;
    const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");

    function applyTheme() {
        const preference = page.dataset.themePreference;
        const dark = preference === "dark" || (preference === "system" && systemTheme.matches);
        page.dataset.bsTheme = dark ? "dark" : "light";
        document.getElementById("theme-toggle")?.setAttribute("aria-pressed", String(dark));
    }

    applyTheme();
    systemTheme.addEventListener("change", applyTheme);

    document.addEventListener("DOMContentLoaded", () => {
        const toggle = document.getElementById("theme-toggle");
        const themeSelect = document.getElementById("theme");
        if (!toggle) return;
        toggle.hidden = false;
        applyTheme();
        toggle.addEventListener("click", () => {
            const theme = page.dataset.bsTheme === "dark" ? "light" : "dark";
            page.dataset.themePreference = theme;
            document.cookie = `${page.dataset.themeCookie}=${theme}; Path=/; Max-Age=31536000; SameSite=Lax`;
            if (themeSelect) themeSelect.value = theme;
            applyTheme();
        });
    });
})();
