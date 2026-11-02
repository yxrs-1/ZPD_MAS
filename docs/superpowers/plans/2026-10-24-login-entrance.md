# 登录入口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把课堂首页改成左右分栏的登录页，学生可以注册进已有班级，忘记密码只提示教师重置。

**Architecture:** `Roster.register_student` 按规格顺序拒绝或追加一名学生。`classroom.py` 用同一个入口页渲染 `/`、`/login` 和未登录的教师、学生地址。`POST /login` 按 `role` 走现有教师或学生校验。注册写进现有 `students`，保存仍走 `response_for` 里已有的整份重写。人物是本页色块，样式和脚本放在 `/static`。

**Tech Stack:** Python 3.14，pytest，现有 FastAPI 应用。在 `F:\work\zpd_MAS` 里改，不新建 worktree。规格是 `docs/superpowers/specs/2026-10-24-login-entrance-design.md`。测试命令用 `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest`。PowerShell 不要使用 `&&`。不要改 git config，不要 push。用户没要求时跳过每一步的 Commit。

## Global Constraints

- `classroom.json` 格式不变。新学生字段是 `account`、`password`、`name`、`class_id`，密码按原文保存。登录标记不写入文件。
- 教师不注册，仍用现有固定账号。已导入学生用原账号密码登录。学生账号文字可以和教师账号相同，以 `role` 决定校验哪一边。
- 登录字段是 `account`、`password`、`role`。`role` 的文字和值只有「教师」和「学生」。按钮是「登录」，提交到 `/login`。`POST /teacher/login` 和 `POST /student/login` 不读取 `role`。
- Cookie 名和路径不变：`teacher` 的路径是 `/teacher`，`student` 的路径是 `/student`。
- 注册字段是 `account`、`password`、`name`、`class_id`。按钮是「注册」。失败按这个顺序只显示一句：先由教师创建班级，先选择班级，班级不存在，账号或密码为空，姓名为空，账号已经存在。状态 200，不写文件。
- 忘记密码的句子是「请教师重置密码」。不提交新密码。
- 登录失败的句子是「账号或密码不正确」，状态 200，不设置登录标记。
- 不引入 React，不请求其他网站，不复制 CareerCompass 的图片和代码。没有邮箱，没有 Google 登录，不记住 30 天。
- 登录之后的出题、作答、班级、导入、重置密码、教材和目标不改。测试不调用监听，不打开浏览器，不访问网络，不在仓库里创建 `classroom.json`。

---

### Task 1: 名册注册一名学生

**Files:**
- Modify: `src/scaffolding/roster.py`
- Test: `tests/test_roster.py`

**Interfaces:**
- Consumes: `Roster.create_class`、`Roster.import_rows`、`RosterError`
- Produces: `Roster.register_student(self, class_id: str, account: str, password: str, name: str) -> StudentRecord`。失败抛 `RosterError`，成功把学生追加到该班末尾。

- [ ] **Step 1: Write the failing test**

在 `tests/test_roster.py` 末尾追加：

```python
def test_register_student_appends_one_person_or_rejects_in_order():
    roster = Roster()

    with pytest.raises(RosterError, match="先由教师创建班级"):
        roster.register_student("class-1", "s1", "secret", "甲")
    created = roster.create_class("一班")
    roster.import_rows(created.class_id, ((2, "s1", "secret", "甲"),))
    with pytest.raises(RosterError, match="先选择班级"):
        roster.register_student("  ", "s2", "secret", "乙")
    with pytest.raises(RosterError, match="班级不存在"):
        roster.register_student("class-9", "s2", "secret", "乙")
    with pytest.raises(RosterError, match="账号或密码为空"):
        roster.register_student(created.class_id, "  ", "secret", "乙")
    with pytest.raises(RosterError, match="姓名为空"):
        roster.register_student(created.class_id, "s2", "secret", "  ")
    with pytest.raises(RosterError, match="账号已经存在"):
        roster.register_student(created.class_id, " s1 ", "other", "丙")

    added = roster.register_student(created.class_id, " s2 ", " secret ", " 乙 ")
    same_name = roster.register_student(created.class_id, "s3", "secret", "乙")

    assert added == roster.authenticate_student("s2", "secret")
    assert [item.account for item in roster.students(created.class_id)] == ["s1", "s2", "s3"]
    assert same_name.name == "乙"
    assert roster.authenticate_student("s1", "other") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_roster.py::test_register_student_appends_one_person_or_rejects_in_order -q`

Expected: FAIL，`register_student` 不存在。

- [ ] **Step 3: Write minimal implementation**

在 `src/scaffolding/roster.py` 的 `import_rows` 之后加入：

```python
def register_student(self, class_id: str, account: str, password: str, name: str) -> StudentRecord:
    if not self._classes:
        raise RosterError("先由教师创建班级")
    class_id = _clean(class_id)
    if class_id == "":
        raise RosterError("先选择班级")
    if class_id not in self._classes:
        raise RosterError("班级不存在")
    account = _clean(account)
    password = _clean(password)
    name = _clean(name)
    if account == "" or password == "":
        raise RosterError("账号或密码为空")
    if name == "":
        raise RosterError("姓名为空")
    if account in self._students:
        raise RosterError("账号已经存在")
    student = StudentRecord(account, password, name, class_id)
    self._students[account] = student
    self._members[class_id].append(account)
    return student
```

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command. Expected: PASS.

- [ ] **Step 5: Commit**

用户要求提交时再执行：`git add src/scaffolding/roster.py tests/test_roster.py`，提交说明 `feat: register one student into an existing class`。

---

### Task 2: 登录页

**Files:**
- Modify: `src/scaffolding/classroom.py`
- Modify: `src/scaffolding/static/classroom.css`
- Create: `src/scaffolding/static/entrance.js`
- Modify: `tests/test_classroom_routes.py`
- Modify: `tests/test_class_login.py`
- Modify: `tests/test_class_acceptance.py`
- Modify: `tests/test_classroom_web.py`
- Test: `tests/test_login_entrance.py`

**Interfaces:**
- Consumes: `_document`、`response_for`
- Produces: `entrance_page(role: str, message: str = "", forgot: bool = False) -> str`。`role` 是「教师」或「学生」。页面含 `class="characters"`、四个 `class="person purple|orange|black|yellow"`、密码按钮「显示」。学生角色含「注册账号」和「忘记密码」。

- [ ] **Step 1: Write the failing test**

新建 `tests/test_login_entrance.py`：

```python
from scaffolding.classroom import response_for
from tests.classroom_helpers import room, text


def test_the_home_page_is_the_student_login():
    html = text(response_for(room(), "GET", "/", "", 0))

    assert "<h1>登录</h1>" in html
    assert "<h1>课堂</h1>" not in html
    assert 'name="role"' in html
    assert 'value="学生"' in html and 'value="教师"' in html
    assert 'name="account"' in html and 'name="password"' in html
    assert 'action="/login"' in html
    assert ">登录</button>" in html
    assert 'value="学生" selected' in html
    assert "<h1>登录</h1>" in text(response_for(room(), "GET", "/login", "", 0))
    assert 'href="/student/register"' in html
    assert "忘记密码" in html
    assert 'class="characters"' in html
    assert 'class="person purple"' in html
    assert 'class="person orange"' in html
    assert 'class="person black"' in html
    assert 'class="person yellow"' in html
    assert ">显示</button>" in html
    assert 'src="/static/entrance.js"' in html


def test_teacher_addresses_preselect_the_teacher_and_hide_student_links():
    html = text(response_for(room(), "GET", "/teacher/login", "", 0))

    assert 'value="教师" selected' in html
    assert "注册账号" not in html
    assert "忘记密码" not in html
    assert "请教师重置密码" not in html


def test_forgot_password_only_shows_the_teacher_reset_sentence():
    shown = text(response_for(room(), "GET", "/student/login?forgot=1", "", 0))
    hidden = text(response_for(room(), "GET", "/teacher/login?forgot=1", "", 0))

    assert "请教师重置密码" in shown
    assert 'name="password"' in shown
    assert "请教师重置密码" not in hidden
```

把下面四处旧首页断言改成新登录页，不要再要求「课堂」或 `href="/teacher"`、`href="/student"`：

- `tests/test_classroom_routes.py` 的 `test_the_root_links_to_the_teacher_and_the_student`：改为断言 `<h1>登录</h1>`、`name="role"`，并且 `"task-" not in html`。
- `tests/test_class_login.py` 的首页那一行：改为 `assert "<h1>登录</h1>" in home and 'href="/student/register"' in home`。
- `tests/test_class_acceptance.py` 的 `test_the_classroom_entry_has_no_tasks`：`<h1>课堂</h1>` 改为 `<h1>登录</h1>`，去掉两个入口链接断言，保留 `"task-" not in home`。
- `tests/test_classroom_web.py` 的 `test_the_web_app_serves_the_classroom_home`：同样改为 `<h1>登录</h1>` 和 `name="role"`。

- [ ] **Step 2: Run test to verify it fails**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_login_entrance.py -q`

Expected: FAIL，页面仍是「课堂」或旧登录页，没有人物和 `role`。

- [ ] **Step 3: Write minimal implementation**

`classroom.py` 的 `urlsplit` 导入改为同时导入 `parse_qsl`。

`_document` 增加参数 `entrance: bool = False`。为真时，`<body>` 写成 `<body class="entrance">`。

用 `entrance_page` 替换 `_login_page` 的函数体，旧函数保留给现有调用：

```python
def _login_page(action: str, message: str = "") -> str:
    role = "教师" if action.startswith("/teacher") else "学生"
    return entrance_page(role, message)


def entrance_page(role: str, message: str = "", forgot: bool = False) -> str:
    teacher = role == "教师"
    selected_teacher = " selected" if teacher else ""
    selected_student = "" if teacher else " selected"
    notice = ""
    if message:
        notice = "<p>" + escape(message) + "</p>"
    extra = ""
    if not teacher:
        if forgot:
            extra += "<p>请教师重置密码</p>"
        extra += (
            '<p><a href="/student/register">注册账号</a>'
            '<a href="?forgot=1">忘记密码</a></p>'
        )
    body = (
        '<div class="entrance"><div class="characters" aria-hidden="true">'
        '<div class="person purple"></div>'
        '<div class="person orange"></div>'
        '<div class="person black"></div>'
        '<div class="person yellow"></div>'
        '</div><div class="panel"><h1>登录</h1>'
        + notice
        + '<form method="post" action="/login">'
        + '<select name="role">'
        + '<option value="学生"' + selected_student + ">学生</option>"
        + '<option value="教师"' + selected_teacher + ">教师</option>"
        + "</select>"
        + '<input name="account">'
        + '<input name="password" type="password">'
        + '<button type="button">显示</button>'
        + '<button type="submit">登录</button></form>'
        + extra
        + '</div></div><script src="/static/entrance.js"></script>'
    )
    return _document(body, entrance=True)
```

`_dispatch_response` 在拆出 `raw_path` 后读取查询：

```python
forgot = dict(parse_qsl(urlsplit(path).query)).get("forgot") == "1"
```

`parts == []` 或 `parts == ["login"]` 且方法不是 POST 时，返回 `entrance_page("学生", forgot=forgot)`。`parts == ["login"]` 且方法是 POST 时先留到 Task 3；本任务里 POST `/login` 可以返回学生登录失败页，状态 200，句子「账号或密码不正确」。

`_teacher_response` 和 `_student_response` 在未登录时调用的 `_login_page(...)` 改为带上当前请求的 `forgot`。做法：给这两个函数增加参数 `forgot: bool = False`，未登录分支返回 `entrance_page("教师" if 教师 else "学生", forgot=forgot)`。`_dispatch_response` 把 `forgot` 传下去。`_rerender_teacher` 和 `_rerender_student` 里未登录的 `_login_page` 也改成对应角色的 `entrance_page`，这里没有忘记密码查询，`forgot` 用默认值。

`src/scaffolding/static/entrance.js`：

```javascript
const characters = document.querySelector(".characters");
const account = document.querySelector('input[name="account"]');
const password = document.querySelector('input[name="password"]');
const toggle = document.querySelector('button[type="button"]');
if (characters && account && password && toggle) {
  account.addEventListener("input", function () {
    characters.dataset.look = "account";
  });
  function lookAway() { characters.dataset.look = "away"; }
  password.addEventListener("focus", lookAway);
  password.addEventListener("input", lookAway);
  toggle.addEventListener("click", function () {
    const shown = password.type === "text";
    password.type = shown ? "password" : "text";
    toggle.textContent = shown ? "显示" : "隐藏";
    characters.dataset.look = shown ? "forward" : "away";
  });
}
```

在 `classroom.css` 末尾追加。只作用于 `body.entrance`，不要改其他页面的 `body` 宽度：

```css
body.entrance { max-width: none; margin: 0; padding: 0; }
body.entrance .entrance { display: flex; min-height: 100vh; }
body.entrance .characters {
  position: relative; flex: 1; background: #8b93a7; overflow: hidden;
}
body.entrance .person { position: absolute; bottom: 12%; }
body.entrance .purple { left: 18%; width: 90px; height: 220px; background: #6d4aff; border-radius: 12px; }
body.entrance .orange { left: 8%; width: 140px; height: 110px; background: #f08a4b; border-radius: 70px 70px 12px 12px; }
body.entrance .black { left: 38%; width: 70px; height: 180px; background: #1c1c1c; border-radius: 12px; }
body.entrance .yellow { left: 52%; width: 100px; height: 150px; background: #f2d64b; border-radius: 50px 50px 16px 16px; }
body.entrance .yellow::after {
  content: ""; position: absolute; left: 30px; bottom: 36px; width: 40px; height: 4px; background: #1c1c1c;
}
body.entrance .person::before {
  content: ""; position: absolute; top: 28px; left: 18px; width: 14px; height: 14px;
  border-radius: 50%; background: #fff; box-shadow: 22px 0 0 #fff;
}
body.entrance .characters[data-look="away"] .person::before { top: 18px; }
body.entrance .characters[data-look="account"] .person::before { left: 28px; }
body.entrance .panel {
  flex: 1; background: #fff; padding: 64px 48px;
}
body.entrance .panel h1 { border: 0; padding: 0; text-align: center; }
```

- [ ] **Step 4: Run tests**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_login_entrance.py tests/test_classroom_routes.py tests/test_class_login.py tests/test_class_acceptance.py tests/test_classroom_web.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

用户要求提交时再执行。说明：`feat: show the classroom entrance as one login page`。

---

### Task 3: 按角色登录

**Files:**
- Modify: `src/scaffolding/classroom.py`
- Test: `tests/test_login_entrance.py`

**Interfaces:**
- Consumes: `entrance_page`、`Roster.authenticate_teacher`、`Roster.authenticate_student`、现有的学生页和教师页响应
- Produces: `POST /login`。成功时 Cookie 和去向与 `POST /teacher/login`、`POST /student/login` 相同。

- [ ] **Step 1: Write the failing test**

追加到 `tests/test_login_entrance.py`：

```python
from tests.classroom_helpers import form


def test_login_follows_the_selected_role():
    page = room()
    created = page.roster.create_class("一班")
    teacher_account = page.roster.teacher_account
    teacher_password = page.roster.teacher_password
    page.roster.import_rows(created.class_id, ((2, teacher_account, "secret", "甲"),))

    teacher = response_for(page, "POST", "/login", form(role="教师", account=teacher_account, password=teacher_password), 0)
    student = response_for(page, "POST", "/login", form(role="学生", account=teacher_account, password="secret"), 0)
    wrong = response_for(page, "POST", "/login", form(role="教师", account=teacher_account, password="secret"), 0)
    missing = response_for(page, "POST", "/login", form(role="其他", account=teacher_account, password=teacher_password), 0)

    assert teacher.set_cookie.startswith("teacher=")
    assert "<h1>任务列表</h1>" in text(teacher)
    assert student.set_cookie.startswith("student=")
    assert "<h1>待办</h1>" in text(student)
    assert wrong.set_cookie == ""
    assert wrong.status == 200
    assert "账号或密码不正确" in text(wrong)
    assert 'value="教师" selected' in text(wrong)
    assert missing.set_cookie == ""
    assert "账号或密码不正确" in text(missing)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_login_entrance.py::test_login_follows_the_selected_role -q`

Expected: FAIL。Task 2 的 POST `/login` 还不会按角色进入任务列表或待办。

- [ ] **Step 3: Write minimal implementation**

在 `classroom.py` 加入 `_role_login`，并在 `_dispatch_response` 里对 `parts == ["login"]` 且 `method == "POST"` 调用它。成功分支复制 `_teacher_login` 和 `_student_login` 里设置 Cookie 和进入页面的那几行，不要改那两个旧函数。

```python
def _role_login(room, body: str, now: float):
    fields = parse_qs(body, keep_blank_values=True)
    role = fields.get("role", [""])[-1]
    account = fields.get("account", [""])[-1]
    password = fields.get("password", [""])[-1]
    if role == "教师":
        if not room.roster.authenticate_teacher(account, password):
            return _html(entrance_page("教师", "账号或密码不正确"))
        token = secrets.token_hex(16)
        room.teacher_tokens.add(token)
        response = teacher_response_for(room.teacher, "GET", "/", "")
        return replace(response, set_cookie=_set_cookie("teacher", token, "/teacher"))
    if role == "学生":
        student = room.roster.authenticate_student(account, password)
        if student is None:
            return _html(entrance_page("学生", "账号或密码不正确"))
        token = secrets.token_hex(16)
        room.student_tokens[token] = student.account
        student_page = _student_page(room, student.account, student.class_id)
        response = student_response_for(student_page, "GET", "/", "", now)
        return replace(response, set_cookie=_set_cookie("student", token, "/student"))
    return _html(entrance_page("学生", "账号或密码不正确"))
```

- [ ] **Step 4: Run tests**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_login_entrance.py tests/test_class_login.py -q`

Expected: PASS。旧的 `POST /teacher/login` 和 `POST /student/login` 仍然通过。

- [ ] **Step 5: Commit**

用户要求提交时再执行。说明：`feat: log in through the selected role`。

---

### Task 4: 学生注册

**Files:**
- Modify: `src/scaffolding/classroom.py`
- Test: `tests/test_login_entrance.py`

**Interfaces:**
- Consumes: `Roster.register_student`、`entrance_page` 的人物标记、`response_for` 的现有保存
- Produces: `register_page(room, message: str = "") -> str`。`GET` 和 `POST /student/register`。已登录学生打开时进入待办。

- [ ] **Step 1: Write the failing test**

追加到 `tests/test_login_entrance.py`：

```python
from scaffolding.classroom import Classroom
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog


def _saved_room(path):
    return Classroom(
        TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent(), path=str(path)
    )


def test_register_adds_a_student_and_opens_the_todo(tmp_path):
    path = tmp_path / "classroom.json"
    page = _saved_room(path)
    created = page.roster.create_class("一班")
    response_for(page, "GET", "/", "", 0)

    empty = response_for(page, "POST", "/student/register", form(
        account="s2", password="secret", name="乙", class_id="  ",
    ), 0)

    assert empty.status == 200
    assert "先选择班级" in text(empty)
    assert page.roster.authenticate_student("s2", "secret") is None
    registered = response_for(page, "POST", "/student/register", form(
        account=" s2 ", password=" secret ", name=" 乙 ", class_id=created.class_id,
    ), 0)
    again = _saved_room(path)
    assert registered.set_cookie.startswith("student=")
    assert "<h1>待办</h1>" in text(registered)
    assert again.roster.authenticate_student("s2", "secret").name == "乙"
    assert [item.account for item in again.roster.students(created.class_id)] == ["s2"]


def test_register_page_lists_classes_and_rejects_without_writing():
    bare = text(response_for(room(), "GET", "/student/register", "", 0))
    page = room()
    created = page.roster.create_class("一班")
    listed = text(response_for(page, "GET", "/student/register", "", 0))
    page.roster.import_rows(created.class_id, ((2, "s1", "secret", "甲"),))
    duplicate = response_for(page, "POST", "/student/register", form(
        account="s1", password="secret", name="乙", class_id=created.class_id,
    ), 0)
    missing = response_for(page, "POST", "/student/register", form(
        account="s9", password="secret", name="乙", class_id="class-9",
    ), 0)
    blank = response_for(page, "POST", "/student/register", form(
        account="  ", password="secret", name="乙", class_id=created.class_id,
    ), 0)
    unnamed = response_for(page, "POST", "/student/register", form(
        account="s9", password="secret", name="  ", class_id=created.class_id,
    ), 0)
    cookie = response_for(
        page, "POST", "/student/login", form(account="s1", password="secret"), 0
    ).set_cookie.split(";", 1)[0]
    opened = response_for(page, "GET", "/student/register", "", 0, cookie)

    assert "<h1>注册</h1>" in bare
    assert "先由教师创建班级" in bare
    assert 'class="characters"' in bare
    assert '<option value="">选择班级</option>' in listed
    assert '<option value="class-1">一班</option>' in listed
    assert duplicate.status == 200 and "账号已经存在" in text(duplicate) and duplicate.set_cookie == ""
    assert missing.status == 200 and "班级不存在" in text(missing)
    assert blank.status == 200 and "账号或密码为空" in text(blank)
    assert unnamed.status == 200 and "姓名为空" in text(unnamed)
    assert [item.account for item in page.roster.students(created.class_id)] == ["s1"]
    assert "<h1>待办</h1>" in text(opened)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_login_entrance.py -q`

Expected: FAIL，`/student/register` 仍被当成未登录的学生页或 404。

- [ ] **Step 3: Write minimal implementation**

```python
def register_page(room, message: str = "") -> str:
    notice = "<p>" + escape(message) + "</p>" if message else ""
    if not room.roster.classes():
        notice = "<p>先由教师创建班级</p>"
    options = '<option value="">选择班级</option>'
    for item in room.roster.classes():
        options += '<option value="' + escape(item.class_id) + '">' + escape(item.name) + "</option>"
    body = (
        '<div class="entrance"><div class="characters" aria-hidden="true">'
        '<div class="person purple"></div><div class="person orange"></div>'
        '<div class="person black"></div><div class="person yellow"></div>'
        '</div><div class="panel"><h1>注册</h1>'
        + notice
        + '<form method="post" action="/student/register">'
        + '<input name="account"><input name="password" type="password">'
        + '<button type="button">显示</button>'
        + '<input name="name"><select name="class_id">'
        + options
        + '</select><button type="submit">注册</button></form>'
        + '</div></div><script src="/static/entrance.js"></script>'
    )
    return _document(body, entrance=True)


def _register_student(room, body: str, now: float):
    if not room.roster.classes():
        return _html(register_page(room))
    fields = parse_qs(body, keep_blank_values=True)
    try:
        student = room.roster.register_student(
            fields.get("class_id", [""])[-1],
            fields.get("account", [""])[-1],
            fields.get("password", [""])[-1],
            fields.get("name", [""])[-1],
        )
    except RosterError as error:
        return _html(register_page(room, str(error)))
    token = secrets.token_hex(16)
    room.student_tokens[token] = student.account
    student_page = _student_page(room, student.account, student.class_id)
    response = student_response_for(student_page, "GET", "/", "", now)
    return replace(response, set_cookie=_set_cookie("student", token, "/student"))
```

在 `_student_response` 检查 Cookie 之前：

- `parts == ["student", "register"]` 且已有有效学生 Cookie：返回这名学生的待办。
- 同一路径且 `method == "POST"`：返回 `_register_student(...)`。
- 同一路径且 `method == "GET"`：返回 `register_page(room)`。

没有班级时，`_register_student` 直接显示「先由教师创建班级」，不调用 `register_student`，这样空 `class_id` 不会先变成「先选择班级」。

- [ ] **Step 4: Run tests**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_login_entrance.py tests/test_roster.py tests/test_class_login.py tests/test_classroom_store.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

用户要求提交时再执行。说明：`feat: let a student register into an existing class`。

然后再跑一遍完整测试：

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest -q`

Expected: 全部 PASS。
