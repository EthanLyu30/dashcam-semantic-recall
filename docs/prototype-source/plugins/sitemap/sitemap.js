(function () {
  var pkg = window.prototypePackage || { pages: [] };
  var container = document.getElementById("groups");
  var categories = {};

  pkg.pages.forEach(function (page) {
    if (!categories[page.category]) {
      categories[page.category] = [];
    }
    categories[page.category].push(page);
  });

  Object.keys(categories).forEach(function (category) {
    var section = document.createElement("section");
    section.className = "group";
    var title = document.createElement("h2");
    title.textContent = category;
    section.appendChild(title);

    var list = document.createElement("div");
    list.className = "item-list";

    categories[category].forEach(function (page) {
      var item = document.createElement("article");
      item.className = "item";
      item.innerHTML =
        '<a href="../../' + page.file + '">' + page.title + '</a>' +
        '<p>' + page.description + "</p>";
      list.appendChild(item);
    });

    section.appendChild(list);
    container.appendChild(section);
  });
})();
