document.querySelectorAll("[data-filters]").forEach((form) => {
  const root = document.querySelector(form.dataset.target);
  if (!root) return;

  const items = [...root.querySelectorAll("[data-filter-item]")];
  const controls = [...form.querySelectorAll("[data-filter]")];
  const count = form.querySelector("[data-result-count]");

  const normalize = (value) => value.toLocaleLowerCase().trim();

  const applyFilters = () => {
    let visible = 0;

    items.forEach((item) => {
      const matches = controls.every((control) => {
        const value = normalize(control.value);
        if (!value) return true;
        const haystack = normalize(item.dataset[control.dataset.field] || "");
        return control.type === "search"
          ? haystack.includes(value)
          : haystack.split("|").includes(value);
      });

      item.hidden = !matches;
      if (matches) visible += 1;
    });

    root.querySelectorAll("[data-filter-group]").forEach((group) => {
      group.hidden = !group.querySelector("[data-filter-item]:not([hidden])");
    });

    if (count) count.textContent = `${visible} result${visible === 1 ? "" : "s"}`;
  };

  form.addEventListener("input", applyFilters);
  form.addEventListener("submit", (event) => event.preventDefault());
});

