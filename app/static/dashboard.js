(() => {
    const form = document.querySelector("[data-dashboard-filters]");
    if (!form) return;

    const dashboard = form.closest(".dashboard");
    const search = form.elements.namedItem("q");
    const applyButton = form.querySelector('button[type="submit"]');
    const applyLabel = applyButton.textContent;
    const message = dashboard.querySelector("[data-dashboard-message]");
    const slicers = [...form.querySelectorAll("[data-dashboard-slicer]")];
    const facetOptions = form.querySelectorAll("[data-facet-option]");
    const number = new Intl.NumberFormat("en-US");
    const updateTimeout = 12_000;
    let pendingRequest;
    let searchTimer;

    function updateSlicerLabels() {
        for (const slicer of slicers) {
            const selected = slicer.querySelector("input[type=radio]:checked");
            if (selected) {
                slicer.querySelector("[data-slicer-selection]").textContent =
                    selected.closest("label").querySelector("[data-option-label]").textContent.trim();
            }
        }
    }

    function updateFacetOptions(facets) {
        for (const option of facetOptions) {
            const input = option.querySelector("input");
            const count = facets[input.name]?.[input.value.toUpperCase()] ?? 0;
            input.disabled = Boolean(input.value && !input.checked && !count);
            option.querySelector("[data-facet-count]").textContent = number.format(count);
        }
    }

    function filterParameters() {
        const parameters = new URLSearchParams();
        for (const [name, value] of new FormData(form)) {
            const normalized = value.trim();
            if (normalized) parameters.set(name, normalized);
        }
        return parameters.toString();
    }

    async function updateDashboard() {
        clearTimeout(searchTimer);
        pendingRequest?.abort();
        const controller = new AbortController();
        pendingRequest = controller;

        const results = dashboard.querySelector("[data-dashboard-results]");
        results.setAttribute("aria-busy", "true");
        applyButton.textContent = "Updating…";
        message.classList.remove("is-error");
        message.textContent = "Updating dashboard.";
        const query = filterParameters();
        const endpoint = new URL(form.dataset.resultsUrl);
        endpoint.search = query;
        let timedOut = false;
        const deadline = setTimeout(() => {
            timedOut = true;
            controller.abort();
        }, updateTimeout);

        try {
            const response = await fetch(endpoint, { signal: controller.signal });
            if (response.redirected) {
                window.location.assign(response.url);
                return;
            }
            if (!response.ok) throw new Error("Dashboard update failed.");
            const content = document.createElement("template");
            content.innerHTML = await response.text();
            if (controller.signal.aborted) return;
            const updated = content.content.querySelector("[data-dashboard-results]");
            if (!updated) throw new Error("Dashboard results are missing.");
            const facets = JSON.parse(updated.querySelector("[data-dashboard-facets]").textContent);
            updateFacetOptions(facets);
            results.replaceWith(updated);

            const address = new URL(form.action);
            address.search = query;
            window.history.replaceState(null, "", address);
            const count = Number(updated.dataset.resultCount);
            message.textContent = `${number.format(count)} matching ${count === 1 ? "student" : "students"}.`;
        } catch {
            if (pendingRequest === controller && (timedOut || !controller.signal.aborted)) {
                message.classList.add("is-error");
                const reason = timedOut ? "The dashboard update timed out." : "The dashboard could not update.";
                message.textContent = `${reason} The previous results are still displayed. Try Apply filters again.`;
            }
        } finally {
            clearTimeout(deadline);
            if (pendingRequest === controller) {
                results.setAttribute("aria-busy", "false");
                applyButton.textContent = applyLabel;
                pendingRequest = null;
            }
        }
    }

    for (const slicer of slicers) {
        const filter = slicer.querySelector("[data-slicer-search]");
        const empty = slicer.querySelector("[data-slicer-empty]");
        const choices = [...slicer.querySelectorAll("[data-slicer-choice]")];
        filter.hidden = false;
        filter.addEventListener("input", () => {
            const query = filter.value.trim().toLowerCase();
            let visible = 0;
            for (const choice of choices) {
                choice.hidden = !choice.querySelector("[data-option-label]").textContent.trim().toLowerCase().includes(query);
                if (!choice.hidden) visible += 1;
            }
            empty.hidden = visible > 0;
        });
        filter.addEventListener("keydown", (event) => {
            if (event.key === "Enter") event.preventDefault();
        });
        slicer.addEventListener("click", (event) => {
            const choice = event.target.closest("[data-slicer-choice]");
            if (!event.detail || !choice || choice.querySelector("input").disabled) return;
            requestAnimationFrame(() => {
                slicer.open = false;
                slicer.querySelector("summary").focus();
            });
        });
        slicer.addEventListener("toggle", () => {
            if (slicer.open) {
                for (const other of slicers) {
                    if (other !== slicer) other.open = false;
                }
            } else if (filter.value) {
                filter.value = "";
                filter.dispatchEvent(new Event("input"));
            }
        });
        slicer.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && slicer.open) {
                slicer.open = false;
                slicer.querySelector("summary").focus();
            }
        });
    }

    document.addEventListener("click", (event) => {
        for (const slicer of slicers) {
            if (!slicer.contains(event.target)) slicer.open = false;
        }
    });

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        updateDashboard();
    });
    form.addEventListener("change", (event) => {
        if (event.target.type !== "radio") return;
        updateSlicerLabels();
        updateDashboard();
    });
    search.addEventListener("input", () => {
        clearTimeout(searchTimer);
        pendingRequest?.abort();
        searchTimer = setTimeout(updateDashboard, 350);
    });

    dashboard.addEventListener("click", (event) => {
        if (event.button !== 0 || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
        if (event.target.closest("[data-dashboard-clear]")) {
            event.preventDefault();
            search.value = "";
            for (const radio of form.querySelectorAll("input[type=radio]")) {
                radio.checked = radio.value === "";
            }
        } else {
            const link = event.target.closest("[data-dashboard-slice]");
            if (!link) return;
            const radio = [...form.elements].find((input) =>
                input.name === link.dataset.dashboardSlice && input.value === link.dataset.sliceValue);
            if (!radio || radio.disabled) return;
            event.preventDefault();
            radio.checked = true;
        }
        updateSlicerLabels();
        updateDashboard();
    });
})();
