document.addEventListener("click", (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.altKey || event.ctrlKey || event.metaKey
        || event.shiftKey || event.target.closest("a, button, input, select, textarea, label")) {
        return;
    }

    const row = event.target.closest("tr[data-select-record]");
    if (row && window.getSelection()?.type !== "Range") {
        row.querySelector("[data-record-link]").click();
    }
});
