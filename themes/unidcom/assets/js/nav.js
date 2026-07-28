document.documentElement.classList.add("js");

const navButton = document.querySelector("[data-nav-toggle]");
const siteNav = document.querySelector("[data-site-nav]");

if (navButton && siteNav) {
  const closeNav = () => {
    navButton.setAttribute("aria-expanded", "false");
    siteNav.classList.remove("is-open");
  };

  navButton.addEventListener("click", () => {
    const open = navButton.getAttribute("aria-expanded") !== "true";
    navButton.setAttribute("aria-expanded", String(open));
    siteNav.classList.toggle("is-open", open);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && navButton.getAttribute("aria-expanded") === "true") {
      closeNav();
      navButton.focus();
    }
  });
}
