(function () {
  "use strict";

  var header = document.querySelector("[data-header]");
  var menuButton = document.querySelector(".menu-toggle");
  var siteNav = document.getElementById("site-nav");
  var copyStatus = document.getElementById("copy-status");
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function setMenu(open) {
    if (!menuButton || !siteNav) {
      return;
    }
    menuButton.setAttribute("aria-expanded", String(open));
    menuButton.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
    siteNav.classList.toggle("is-open", open);
    document.body.classList.toggle("menu-open", open);
  }

  if (menuButton && siteNav) {
    menuButton.addEventListener("click", function () {
      setMenu(menuButton.getAttribute("aria-expanded") !== "true");
    });

    siteNav.addEventListener("click", function (event) {
      if (event.target.closest("a")) {
        setMenu(false);
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && menuButton.getAttribute("aria-expanded") === "true") {
        setMenu(false);
        menuButton.focus();
      }
    });

    window.addEventListener("resize", function () {
      if (window.innerWidth > 900) {
        setMenu(false);
      }
    });
  }

  function updateHeader() {
    if (header) {
      header.classList.toggle("is-scrolled", window.scrollY > 8);
    }
  }

  updateHeader();
  window.addEventListener("scroll", updateHeader, { passive: true });

  var revealItems = Array.prototype.slice.call(document.querySelectorAll(".reveal"));
  if (reducedMotion || !("IntersectionObserver" in window)) {
    revealItems.forEach(function (item) {
      item.classList.add("is-visible");
    });
  } else {
    var revealObserver = new IntersectionObserver(function (entries, observer) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, {
      rootMargin: "0px 0px -8% 0px",
      threshold: 0.08
    });

    revealItems.forEach(function (item) {
      revealObserver.observe(item);
    });
  }

  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".site-nav a[href^='#']"));
  var sections = Array.prototype.slice.call(document.querySelectorAll(".section-anchor[id]"));
  if ("IntersectionObserver" in window && navLinks.length && sections.length) {
    var currentId = "";
    var sectionObserver = new IntersectionObserver(function (entries) {
      var visible = entries
        .filter(function (entry) { return entry.isIntersecting; })
        .sort(function (a, b) { return b.intersectionRatio - a.intersectionRatio; });

      if (visible.length) {
        currentId = visible[0].target.id;
        navLinks.forEach(function (link) {
          link.classList.toggle("is-active", link.getAttribute("href") === "#" + currentId);
        });
      }
    }, {
      rootMargin: "-28% 0px -62% 0px",
      threshold: [0, 0.05, 0.2]
    });

    sections.forEach(function (section) {
      sectionObserver.observe(section);
    });
  }

  var tabs = Array.prototype.slice.call(document.querySelectorAll("[role='tab']"));

  function activateTab(tab, focus) {
    var tabList = tab.closest("[role='tablist']");
    if (!tabList) {
      return;
    }

    var localTabs = Array.prototype.slice.call(tabList.querySelectorAll("[role='tab']"));
    localTabs.forEach(function (candidate) {
      var selected = candidate === tab;
      var panel = document.getElementById(candidate.getAttribute("aria-controls"));
      candidate.setAttribute("aria-selected", String(selected));
      candidate.setAttribute("tabindex", selected ? "0" : "-1");
      if (panel) {
        panel.hidden = !selected;
      }
    });

    if (focus) {
      tab.focus();
    }
  }

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      activateTab(tab, false);
    });

    tab.addEventListener("keydown", function (event) {
      var tabList = tab.closest("[role='tablist']");
      var localTabs = Array.prototype.slice.call(tabList.querySelectorAll("[role='tab']"));
      var index = localTabs.indexOf(tab);
      var targetIndex = index;

      if (event.key === "ArrowRight") {
        targetIndex = (index + 1) % localTabs.length;
      } else if (event.key === "ArrowLeft") {
        targetIndex = (index - 1 + localTabs.length) % localTabs.length;
      } else if (event.key === "Home") {
        targetIndex = 0;
      } else if (event.key === "End") {
        targetIndex = localTabs.length - 1;
      } else {
        return;
      }

      event.preventDefault();
      activateTab(localTabs[targetIndex], true);
    });
  });

  function fallbackCopy(text) {
    var textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    var copied = document.execCommand("copy");
    textarea.remove();
    return Promise.resolve(copied);
  }

  function writeClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).then(function () { return true; });
    }
    return fallbackCopy(text);
  }

  function showCopied(button, ok) {
    var label = button.querySelector("span");
    var original = label ? label.textContent : "";
    button.classList.toggle("is-copied", ok);

    if (label) {
      label.textContent = ok ? "완료" : "실패";
    }
    if (copyStatus) {
      copyStatus.textContent = ok ? "클립보드에 복사했습니다." : "복사하지 못했습니다.";
    }

    window.setTimeout(function () {
      button.classList.remove("is-copied");
      if (label) {
        label.textContent = original;
      }
    }, 1600);
  }

  Array.prototype.slice.call(document.querySelectorAll("[data-copy-target], [data-copy-active-panel]"))
    .forEach(function (button) {
      button.addEventListener("click", function () {
        var target;
        if (button.hasAttribute("data-copy-active-panel")) {
          target = document.querySelector(".tab-panel:not([hidden]) code");
        } else {
          target = document.getElementById(button.getAttribute("data-copy-target"));
        }

        if (!target) {
          showCopied(button, false);
          return;
        }

        writeClipboard(target.textContent.trim())
          .then(function (ok) { showCopied(button, ok); })
          .catch(function () { showCopied(button, false); });
      });
    });

  var year = String(new Date().getFullYear());
  Array.prototype.slice.call(document.querySelectorAll("[data-current-year]"))
    .forEach(function (node) {
      node.textContent = year;
    });
}());
