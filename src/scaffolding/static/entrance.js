var stage = document.querySelector(".characters");
var people = document.querySelectorAll(".person");
var account = document.querySelector('input[name="account"]');
var password = document.querySelector('input[name="password"]');
var toggle = document.querySelector('button[type="button"]');
var role = document.querySelector('select[name="role"]');

if (role) {
  role.addEventListener("change", function () {
    var next = role.value === "教师" ? "/teacher/login" : "/";
    if (window.location.pathname !== next) {
      window.location.assign(next);
    }
  });
}

function clamp(value, limit) {
  return Math.max(-limit, Math.min(limit, value));
}

function look(event) {
  if (!stage || stage.classList.contains("hiding")) {
    return;
  }
  people.forEach(function (person) {
    var rect = person.getBoundingClientRect();
    var dx = event.clientX - (rect.left + rect.width / 2);
    var dy = event.clientY - (rect.top + rect.height / 3);
    person.style.setProperty("--skew", clamp(-dx / 120, 6) + "deg");
    person.style.setProperty("--fx", clamp(dx / 28, 14) + "px");
    person.style.setProperty("--fy", clamp(dy / 36, 10) + "px");
    person.querySelectorAll("i").forEach(function (pupil) {
      pupil.style.setProperty("--px", clamp(dx / 80, 5) + "px");
      pupil.style.setProperty("--py", clamp(dy / 90, 4) + "px");
    });
  });
}

document.addEventListener("mousemove", look);

function blink(name) {
  var person = document.querySelector(".person." + name);
  if (!person) {
    return;
  }
  window.setTimeout(function () {
    person.classList.add("blink");
    window.setTimeout(function () {
      person.classList.remove("blink");
      blink(name);
    }, 140);
  }, 2800 + Math.random() * 3200);
}
blink("purple");
blink("black");

var typingTimer = 0;
if (account && stage) {
  account.addEventListener("input", function () {
    stage.classList.add("typing");
    window.clearTimeout(typingTimer);
    typingTimer = window.setTimeout(function () {
      stage.classList.remove("typing");
    }, 800);
  });
}

function passwordState() {
  if (!stage || !password) {
    return;
  }
  var hidden = password.type === "password";
  var filled = password.value.length > 0;
  stage.classList.toggle("hiding", hidden && (filled || document.activeElement === password));
  stage.classList.toggle("peeking", !hidden && filled);
}

if (password) {
  password.addEventListener("focus", passwordState);
  password.addEventListener("input", passwordState);
  password.addEventListener("blur", passwordState);
}

if (toggle && password) {
  toggle.addEventListener("click", function () {
    var shown = password.type === "text";
    password.type = shown ? "password" : "text";
    toggle.textContent = shown ? "显示" : "隐藏";
    passwordState();
  });
}

document.querySelectorAll(".panel select").forEach(function (select) {
  var label = select.closest("label");
  if (!label || label.querySelector(".picker")) {
    return;
  }
  var picker = document.createElement("div");
  var button = document.createElement("button");
  var menu = document.createElement("ul");
  picker.className = "picker";
  button.type = "button";
  button.className = "picker-face";
  button.setAttribute("aria-haspopup", "listbox");
  button.setAttribute("aria-expanded", "false");
  menu.className = "picker-menu";
  menu.setAttribute("role", "listbox");
  menu.hidden = true;
  Array.prototype.forEach.call(select.options, function (option) {
    var item = document.createElement("li");
    item.setAttribute("role", "option");
    item.dataset.value = option.value;
    item.textContent = option.textContent;
    item.addEventListener("click", function (event) {
      event.stopPropagation();
      choose(option.value);
    });
    menu.appendChild(item);
  });
  function paint() {
    var current = select.options[select.selectedIndex];
    button.textContent = current ? current.textContent : "";
    Array.prototype.forEach.call(menu.children, function (item) {
      item.setAttribute("aria-selected", item.dataset.value === select.value ? "true" : "false");
    });
  }
  function setActive(index) {
    var items = menu.children;
    if (!items.length) {
      return;
    }
    if (index < 0) {
      index = items.length - 1;
    }
    if (index >= items.length) {
      index = 0;
    }
    Array.prototype.forEach.call(items, function (item, itemIndex) {
      if (itemIndex === index) {
        item.dataset.active = "true";
      } else {
        delete item.dataset.active;
      }
    });
  }
  function open() {
    menu.hidden = false;
    picker.classList.add("open");
    button.setAttribute("aria-expanded", "true");
    setActive(select.selectedIndex);
  }
  function close() {
    menu.hidden = true;
    picker.classList.remove("open");
    button.setAttribute("aria-expanded", "false");
  }
  function choose(value) {
    var changed = select.value !== value;
    select.value = value;
    paint();
    close();
    if (changed) {
      window.setTimeout(function () {
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }, 0);
    }
  }
  button.addEventListener("click", function (event) {
    event.stopPropagation();
    if (menu.hidden) {
      open();
    } else {
      close();
    }
  });
  button.addEventListener("keydown", function (event) {
    var items = menu.children;
    var active = Array.prototype.findIndex.call(items, function (item) {
      return item.dataset.active === "true";
    });
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (menu.hidden) {
        open();
        return;
      }
      setActive(active + (event.key === "ArrowDown" ? 1 : -1));
    } else if (event.key === "Enter" && !menu.hidden && active >= 0) {
      event.preventDefault();
      choose(items[active].dataset.value);
    } else if (event.key === "Escape") {
      close();
    }
  });
  label.addEventListener("click", function (event) {
    event.preventDefault();
  });
  document.addEventListener("click", function (event) {
    if (!picker.contains(event.target)) {
      close();
    }
  });
  select.classList.add("native");
  select.tabIndex = -1;
  select.setAttribute("aria-hidden", "true");
  picker.appendChild(button);
  picker.appendChild(menu);
  label.appendChild(picker);
  paint();
});
