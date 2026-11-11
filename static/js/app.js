const toggle = document.getElementById("menuToggle");
const sidebar = document.getElementById("sidebar");
if (toggle && sidebar) toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
document.addEventListener("click", (event) => {
  if (sidebar && sidebar.classList.contains("open") && !sidebar.contains(event.target) && !toggle.contains(event.target)) sidebar.classList.remove("open");
});
