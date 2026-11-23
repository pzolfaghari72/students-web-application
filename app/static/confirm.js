const confirmation = document.querySelector(".confirm-panel");

if (confirmation && typeof confirmation.showModal === "function") {
    confirmation.removeAttribute("open");
    confirmation.showModal();
    confirmation.addEventListener("cancel", (event) => {
        event.preventDefault();
        window.location.assign(confirmation.querySelector("a").href);
    });
}
