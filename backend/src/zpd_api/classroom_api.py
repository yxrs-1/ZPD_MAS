import asyncio
import json
import secrets
import time
from html import unescape
from pathlib import Path
from urllib.parse import quote, urlencode

import anyio
from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse

import scaffolding.store as store
from scaffolding.classroom import _clear_pages, _student_page
from scaffolding.documents import DocumentError, draft_objectives, format_objectives, parse_objective_text, DraftError
from scaffolding.records import ChoiceQuestion, OpenQuestion, TrueFalseQuestion
from scaffolding.roster import RosterError
from scaffolding.sheet import SheetError, read_student_rows
from scaffolding.teacher_page import _fact, _shown
from zpd_api.pages import get_room

router = APIRouter()


def _call_locked(work):
    room = get_room()
    with room._lock:
        tracking = room.path is not None or room.records is not None
        before = store.classroom_state(room) if tracking else None
        status, payload, cookie = work(room)
        if tracking and store.classroom_state(room) != before:
            if room.records is not None:
                room.records.save(room)
            else:
                store.save_classroom(room.path, room)
        if isinstance(payload, dict) and payload.pop("prepare_examples", False):
            try:
                from zpd_api.worker import enqueue_scaffold_examples
                enqueue_scaffold_examples(payload["task_id"])
            except Exception:
                pass
        response = JSONResponse(payload, status_code=status)
        if cookie is not None:
            name, value = cookie
            if value == "":
                response.delete_cookie(name, path="/")
            else:
                response.set_cookie(name, value, path="/", httponly=True, samesite="lax")
        return response


async def _call(work):
    return await anyio.to_thread.run_sync(_call_locked, work)


async def _locked_response(work):
    def run():
        room = get_room()
        with room._lock:
            return work(room)

    return await anyio.to_thread.run_sync(run)


def _bytes_response(found) -> Response:
    if found is None:
        return Response(content=b"", status_code=404)
    filename, content = found
    media = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }.get(Path(filename).suffix.lower(), "application/octet-stream")
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": "inline; filename*=UTF-8''" + quote(filename)},
    )


def _teacher(room, request: Request):
    token = request.cookies.get("teacher", "")
    if token not in room.teacher_tokens:
        return None
    return token


def _student_account(room, request: Request):
    token = request.cookies.get("student", "")
    account = room.student_tokens.get(token)
    if account is None or account not in room.roster._students:
        return None
    return account


def _denied():
    return 401, {"ok": False, "message": "请先登录"}, None


def _student_page_for(room, request: Request, task_id: str):
    account = _student_account(room, request)
    if account is None:
        return None, _denied()
    page = _student_page(room, account, room.roster._students[account].class_id)
    try:
        page.catalog.get(task_id)
    except KeyError:
        return None, (404, {"message": "任务不存在"}, None)
    return page, None


@router.post("/login")
async def login(request: Request):
    body = await request.json()
    role = body.get("role", "")
    account = body.get("account", "")
    password = body.get("password", "")

    def work(room):
        if role == "教师" and room.roster.authenticate_teacher(account, password):
            token = secrets.token_hex(16)
            room.teacher_tokens.add(token)
            return 200, {"ok": True, "role": "教师", "account": room.roster.teacher_account}, ("teacher", token)
        if role == "学生":
            student = room.roster.authenticate_student(account, password)
            if student is not None:
                token = secrets.token_hex(16)
                room.student_tokens[token] = student.account
                return 200, {"ok": True, "role": "学生", "account": student.account, "name": student.name}, ("student", token)
        return 200, {"ok": False, "message": "账号或密码不正确"}, None

    return await _call(work)


@router.post("/logout")
async def logout(request: Request):
    body = {}
    if request.headers.get("content-type", "").startswith("application/json"):
        body = await request.json()
    role = body.get("role", "")

    def work(room):
        teacher = request.cookies.get("teacher", "")
        student = request.cookies.get("student", "")
        if role != "学生" and teacher in room.teacher_tokens:
            room.teacher_tokens.discard(teacher)
            return 200, {"ok": True}, ("teacher", "")
        if role != "教师" and room.student_tokens.get(student):
            room.student_tokens.pop(student, None)
            return 200, {"ok": True}, ("student", "")
        return 200, {"ok": True}, None

    return await _call(work)


@router.get("/me")
async def me(request: Request):
    wanted = request.query_params.get("role", "")

    def work(room):
        if wanted != "学生" and _teacher(room, request) is not None:
            return 200, {"ok": True, "role": "教师", "account": room.roster.teacher_account}, None
        account = _student_account(room, request)
        if wanted != "教师" and account is not None:
            student = room.roster._students[account]
            return 200, {"ok": True, "role": "学生", "account": account, "name": student.name}, None
        return 200, {"ok": False, "role": ""}, None

    return await _call(work)


@router.get("/classes")
async def public_classes():
    def work(room):
        return 200, {"classes": [_class(item) for item in room.roster.classes()]}, None

    return await _call(work)


@router.post("/register")
async def register(request: Request):
    body = await request.json()

    def work(room):
        try:
            student = room.roster.register_student(
                body.get("class_id", ""),
                body.get("account", ""),
                body.get("password", ""),
                body.get("name", ""),
            )
        except RosterError as error:
            return 200, {"ok": False, "message": str(error)}, None
        token = secrets.token_hex(16)
        room.student_tokens[token] = student.account
        return 200, {"ok": True, "role": "学生", "account": student.account, "name": student.name}, ("student", token)

    return await _call(work)


@router.get("/teacher/tasks")
async def teacher_tasks(request: Request):
    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        return 200, {
            "account": room.roster.teacher_account,
            "tasks": [
                {"task_id": task.task_id, "status": _fact(task), "title": task.title}
                for task in room.catalog._tasks.values()
            ],
        }, None

    return await _call(work)


@router.post("/teacher/tasks")
async def create_task(request: Request):
    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        task = room.teacher.catalog.create(())
        return 200, _task_detail(room, task.task_id, ""), None

    return await _call(work)


@router.get("/teacher/tasks/{task_id}")
async def teacher_task(task_id: str, request: Request):
    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        if task_id not in room.catalog._tasks:
            return 404, {"message": "任务不存在"}, None
        return 200, _task_detail(room, task_id, ""), None

    return await _call(work)


@router.post("/teacher/tasks/{task_id}")
async def update_task(task_id: str, request: Request):
    body = await request.json()

    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        if task_id not in room.catalog._tasks and body.get("action") != "delete":
            return 404, {"message": "任务不存在"}, None
        fields = _fields(body.get("questions") or [])
        if body.get("action") == "改名":
            fields["title"] = [body.get("title", "")]
        if body.get("action") == "布置":
            fields["class_id"] = body.get("class_ids") or []
        html = room.teacher.apply(task_id, fields, body.get("action", ""))
        if task_id not in room.catalog._tasks:
            return 200, {"deleted": True, "message": ""}, None
        return 200, _task_detail(room, task_id, _notice(html)), None

    return await _call(work)


@router.post("/teacher/objectives")
async def objectives(request: Request):
    body = await request.json()
    text = body.get("text", "")
    action = body.get("action", "生成目标")

    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        page = room.teacher
        if action == "确认":
            objectives_text = body.get("objectives", "")
            if text.strip() == "":
                return 200, {"message": "先填写需求", "text": text, "objectives": objectives_text}, None
            try:
                parsed = parse_objective_text(objectives_text)
            except DraftError as error:
                return 200, {"message": error.message, "text": text, "objectives": objectives_text}, None
            if page.generation is None:
                return 200, {"message": "生成失败，没有创建任务", "text": text, "objectives": objectives_text}, None
            try:
                passages = tuple(page.retrieve(text)) if page.retrieve is not None else ()
                task = page.generation.generate_from_confirmed(text, parsed, passages)
            except Exception:
                return 200, {"message": "生成失败，没有创建任务", "text": text, "objectives": objectives_text}, None
            return 200, {"message": "", "task_id": task.task_id, "prepare_examples": True}, None
        if text.strip() == "":
            return 200, {"message": "先填写需求", "text": text, "objectives": ""}, None
        if page.complete is None:
            return 200, {"message": "没有写出目标", "text": text, "objectives": ""}, None
        try:
            drafted = draft_objectives(page.complete, page.library.documents(), text, retrieve=page.retrieve)
        except DraftError as error:
            return 200, {"message": error.message, "text": text, "objectives": ""}, None
        return 200, {"message": "", "text": text, "objectives": format_objectives(drafted)}, None

    return await _call(work)


@router.get("/teacher/classes")
async def teacher_classes(request: Request):
    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        return 200, {"classes": [_class(item) for item in room.roster.classes()]}, None

    return await _call(work)


@router.post("/teacher/classes")
async def create_class(request: Request):
    body = await request.json()

    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        try:
            created = room.roster.create_class(body.get("name", ""))
        except RosterError as error:
            return 200, {"ok": False, "message": str(error), "classes": [_class(item) for item in room.roster.classes()]}, None
        return 200, {"ok": True, "class_id": created.class_id}, None

    return await _call(work)


@router.get("/teacher/classes/{class_id}")
async def teacher_class(class_id: str, request: Request):
    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        record = _find_class(room, class_id)
        if record is None:
            return 404, {"message": "班级不存在"}, None
        return 200, _class_detail(room, record), None

    return await _call(work)


@router.post("/teacher/classes/{class_id}/import")
async def import_class(class_id: str, request: Request, file: UploadFile = File(...)):
    content = await file.read()

    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        if _find_class(room, class_id) is None:
            return 404, {"message": "班级不存在"}, None
        if content == b"":
            return 200, {**_class_detail(room, _find_class(room, class_id)), "message": "不能读取这份表格", "failures": []}, None
        try:
            rows = read_student_rows(content)
        except SheetError as error:
            return 200, {**_class_detail(room, _find_class(room, class_id)), "message": str(error), "failures": []}, None
        result = room.roster.import_rows(class_id, rows)
        detail = _class_detail(room, _find_class(room, class_id))
        detail["failures"] = [{"row": item.row, "reason": item.reason} for item in result.failures]
        return 200, detail, None

    return await _call(work)


@router.post("/teacher/classes/{class_id}")
async def class_action(class_id: str, request: Request):
    body = await request.json()

    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        if _find_class(room, class_id) is None:
            return 404, {"message": "班级不存在"}, None
        if body.get("action") == "删除班级":
            accounts = tuple(student.account for student in room.roster.students(class_id))
            room.classwork.drop_class(class_id)
            _clear_pages(room, accounts)
            room.roster.delete_class(class_id)
            return 200, {"deleted": True}, None
        return 200, _class_detail(room, _find_class(room, class_id)), None

    return await _call(work)


@router.get("/teacher/classes/{class_id}/students/{account}")
async def teacher_student(class_id: str, account: str, request: Request):
    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        try:
            student = room.roster.student(class_id, account)
        except RosterError:
            return 404, {"message": "学生不存在"}, None
        return 200, _student_detail(room, student), None

    return await _call(work)


@router.post("/teacher/classes/{class_id}/students/{account}")
async def teacher_student_action(class_id: str, account: str, request: Request):
    body = await request.json()

    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        try:
            room.roster.student(class_id, account)
        except RosterError:
            return 404, {"message": "学生不存在"}, None
        action = body.get("action", "")
        if action == "移除":
            room.classwork.drop_student(account)
            _clear_pages(room, (account,))
            room.roster.remove_student(class_id, account)
            return 200, {"removed": True}, None
        try:
            if action == "修改姓名":
                room.roster.rename_student(class_id, account, body.get("name", ""))
                message = ""
            elif action == "重置密码":
                room.roster.reset_password(class_id, account, body.get("password", ""))
                message = "密码已重置"
            else:
                message = ""
        except RosterError as error:
            message = str(error)
        student = room.roster.student(class_id, account)
        detail = _student_detail(room, student)
        detail["message"] = message
        return 200, detail, None

    return await _call(work)


@router.get("/teacher/documents")
async def documents(request: Request):
    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        return 200, {"documents": [_document(item) for item in room.teacher.library.documents()]}, None

    return await _call(work)


@router.post("/teacher/documents")
async def upload_document(request: Request, file: UploadFile = File(...)):
    content = await file.read()
    name = file.filename or ""

    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        try:
            room.teacher.library.add(name, content)
            message = ""
        except DocumentError as error:
            message = error.message
        return 200, {"message": message, "documents": [_document(item) for item in room.teacher.library.documents()]}, None

    return await _call(work)


@router.post("/teacher/documents/{doc_id}/delete")
async def delete_document(doc_id: str, request: Request):
    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        try:
            room.teacher.library.delete(doc_id)
            message = ""
        except DocumentError as error:
            message = error.message
        return 200, {"message": message, "documents": [_document(item) for item in room.teacher.library.documents()]}, None

    return await _call(work)


@router.get("/teacher/accounts")
async def accounts(request: Request):
    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        return 200, {"students": _account_rows(room), "classes": [_class(item) for item in room.roster.classes()], "message": ""}, None

    return await _call(work)


@router.post("/teacher/accounts")
async def account_action(request: Request):
    body = await request.json()

    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        account = str(body.get("account", "")).strip()
        student = room.roster._students.get(account)
        action = body.get("action", "")
        message = ""
        if action == "重置密码":
            if student is None:
                message = "学生不存在"
            else:
                try:
                    room.roster.reset_password(student.class_id, account, body.get("password", ""))
                    message = "密码已重置"
                except RosterError as error:
                    message = str(error)
        elif action == "换班":
            if student is None:
                message = "学生不存在"
            else:
                try:
                    room.roster.move_student(account, body.get("class_id", ""))
                except RosterError as error:
                    message = str(error)
        return 200, {"students": _account_rows(room), "classes": [_class(item) for item in room.roster.classes()], "message": message}, None

    return await _call(work)


@router.post("/teacher/password")
async def teacher_password(request: Request):
    body = await request.json()

    def work(room):
        if _teacher(room, request) is None:
            return _denied()
        try:
            room.roster.change_teacher_password(body.get("old_password", ""), body.get("password", ""))
            message = "密码已修改"
        except RosterError as error:
            message = str(error)
        return 200, {"message": message}, None

    return await _call(work)


@router.get("/student/tasks")
async def student_tasks(request: Request):
    def work(room):
        account = _student_account(room, request)
        if account is None:
            return _denied()
        page = _student_page(room, account, room.roster._students[account].class_id)
        return 200, {
            "account": account,
            "name": room.roster._students[account].name,
            "tasks": [
                {"task_id": item.task_id, "status": item.status, "title": item.title}
                for item in page.catalog.student_tasks()
            ],
        }, None

    return await _call(work)


@router.get("/student/tasks/{task_id}")
async def student_task(task_id: str, request: Request):
    def work(room):
        page, error = _student_page_for(room, request, task_id)
        if page is None:
            return error
        page.open_task(task_id, time.time())
        return 200, _student_task(page, task_id), None

    return await _call(work)


@router.post("/student/tasks/{task_id}/answers")
async def student_answers(task_id: str, request: Request):
    body = await request.json()

    def work(room):
        page, error = _student_page_for(room, request, task_id)
        if page is None:
            return error
        pairs = []
        for index, item in enumerate(body.get("answers") or []):
            if "text" in item:
                pairs.append(("text-" + str(index), item.get("text") or ""))
            for choice in item.get("selected") or []:
                pairs.append(("selected-" + str(index), choice))
        from scaffolding.student_page import response_for as student_response_for

        student_response_for(page, "POST", "/tasks/" + task_id + "/answers", urlencode(pairs), time.time())
        return 200, _student_task(page, task_id), None

    return await _call(work)


@router.post("/student/tasks/{task_id}/ask")
async def student_ask(task_id: str, request: Request):
    body = await request.json()
    if "text/event-stream" in request.headers.get("accept", ""):
        return _ask_stream(request, task_id, body)

    def work(room):
        page, error = _student_page_for(room, request, task_id)
        if page is None:
            return error
        page.ask(task_id, body.get("question", ""), body.get("source", ""), time.time())
        return 200, _student_task(page, task_id), None

    return await _call(work)


def _ask_stream(request: Request, task_id: str, body: dict) -> StreamingResponse:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def on_kind(kind: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, ("kind", kind))

    def on_text(text: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, ("text", text))

    def work():
        try:
            room = get_room()
            with room._lock:
                tracking = room.path is not None or room.records is not None
                before = store.classroom_state(room) if tracking else None
                page, error = _student_page_for(room, request, task_id)
                if page is None:
                    result = error
                else:
                    page.ask(
                        task_id,
                        body.get("question", ""),
                        body.get("source", ""),
                        time.time(),
                        on_text=on_text,
                        on_kind=on_kind,
                    )
                    if tracking and store.classroom_state(room) != before:
                        if room.records is not None:
                            room.records.save(room)
                        else:
                            store.save_classroom(room.path, room)
                    result = 200, _student_task(page, task_id), None
        except Exception:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", "没有收到结果，请再试一次"))
            return
        status, payload, _cookie = result
        if status != 200:
            message = payload.get("message", "请先登录") if isinstance(payload, dict) else "请先登录"
            loop.call_soon_threadsafe(queue.put_nowait, ("error", message))
            return
        loop.call_soon_threadsafe(queue.put_nowait, ("task", payload))

    async def events():
        asyncio.create_task(anyio.to_thread.run_sync(work))
        while True:
            kind, payload = await queue.get()
            yield _sse(kind, payload)
            if kind in ("task", "error"):
                break

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, payload) -> str:
    return "event: " + event + "\ndata: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


@router.get("/student/tasks/{task_id}/assets/{filename}")
async def student_asset(task_id: str, filename: str, request: Request):
    def work(room):
        page, error = _student_page_for(room, request, task_id)
        if page is None:
            status, payload, _cookie = error
            return JSONResponse(payload, status_code=status)
        return _bytes_response(page.asset(task_id, filename))

    return await _locked_response(work)


@router.get("/student/tasks/{task_id}/turns/{index}/assets/{filename}")
async def student_turn_asset(task_id: str, index: int, filename: str, request: Request):
    def work(room):
        page, error = _student_page_for(room, request, task_id)
        if page is None:
            status, payload, _cookie = error
            return JSONResponse(payload, status_code=status)
        return _bytes_response(page.turn_asset(task_id, index, filename))

    return await _locked_response(work)


@router.post("/student/tasks/{task_id}/submit")
async def student_submit(task_id: str, request: Request):
    def work(room):
        page, error = _student_page_for(room, request, task_id)
        if page is None:
            return error
        page.submit(task_id, time.time())
        return 200, _student_task(page, task_id), None

    return await _call(work)


def _class(item) -> dict:
    return {"class_id": item.class_id, "name": item.name}


def _find_class(room, class_id: str):
    for item in room.roster.classes():
        if item.class_id == class_id:
            return item
    return None


def _question_payload(item) -> dict:
    return {
        "kind": item.kind,
        "prompt": item.prompt,
        "options": list(item.options),
        "requirements": item.requirements,
        "selected": list(item.selected),
        "answer": item.answer,
        "explanation": item.explanation,
    }


def _task_detail(room, task_id: str, message: str) -> dict:
    task = room.catalog.get(task_id)
    questions, has_draft = _shown(room.teacher, task_id)
    assigned = set(room.classwork.assigned(task_id)) if task.published else set()
    return {
        "task_id": task.task_id,
        "title": task.title,
        "status": _fact(task),
        "message": message,
        "editable": not task.started,
        "has_draft": has_draft,
        "published": task.published,
        "questions": [_question_payload(item) for item in questions] if not task.started else [_published_question(item) for item in task.questions],
        "classes": [
            {"class_id": item.class_id, "name": item.name, "assigned": item.class_id in assigned}
            for item in room.roster.classes()
        ] if task.published else [],
    }


def _published_question(question) -> dict:
    if isinstance(question, ChoiceQuestion):
        kind = question.selection.value
        return _question_payload(type("Q", (), {
            "kind": kind,
            "prompt": question.prompt,
            "options": question.choices,
            "requirements": "",
            "selected": question.answer,
            "answer": "",
            "explanation": question.explanation,
        })())
    if isinstance(question, TrueFalseQuestion):
        return {
            "kind": "判断",
            "prompt": question.prompt,
            "options": ["正确", "错误"],
            "requirements": "",
            "selected": [question.answer],
            "answer": "",
            "explanation": question.explanation,
        }
    if isinstance(question, OpenQuestion):
        return {
            "kind": "综合",
            "prompt": question.prompt,
            "options": [],
            "requirements": question.requirements,
            "selected": [],
            "answer": question.answer,
            "explanation": question.explanation,
        }
    raise TypeError("unknown question")


def _fields(questions: list) -> dict:
    fields: dict[str, list] = {}
    for index, item in enumerate(questions):
        kind = item.get("kind", "")
        fields["kind-" + str(index)] = [kind]
        fields["prompt-" + str(index)] = [item.get("prompt", "")]
        fields["requirements-" + str(index)] = [item.get("requirements", "")]
        fields["answer-" + str(index)] = [item.get("answer", "")]
        fields["explanation-" + str(index)] = [item.get("explanation", "")]
        options = list(item.get("options") or [])
        for option_index, option in enumerate(options):
            fields["option-" + str(index) + "-" + str(option_index)] = [option]
        selected = list(item.get("selected") or [])
        if kind in ("单选", "多选"):
            tokens = []
            for value in selected:
                tokens.append(str(options.index(value)) if value in options else "s:" + value)
            fields["selected-" + str(index)] = tokens
        elif selected:
            fields["selected-" + str(index)] = selected
    return fields


def _notice(html: str) -> str:
    marker = "</header>"
    start = html.find(marker)
    if start < 0:
        return ""
    rest = html[start + len(marker):]
    if not rest.startswith("<p>"):
        return ""
    end = rest.find("</p>")
    if end < 0:
        return ""
    return unescape(rest[3:end])


def _class_detail(room, record) -> dict:
    return {
        "class_id": record.class_id,
        "name": record.name,
        "message": "",
        "failures": [],
        "students": [
            {"account": student.account, "name": student.name}
            for student in room.roster.students(record.class_id)
        ],
    }


def _student_detail(room, student) -> dict:
    from scaffolding.classwork import StudentView

    view = StudentView(room.catalog, room.classwork, student.account, student.class_id)
    tasks = []
    for listed in view.student_tasks():
        try:
            work = view.work(listed.task_id)
        except KeyError:
            work = None
        if work is None:
            status = "还没作答"
        elif work.submitted:
            status = "已完成"
        else:
            status = "待办"
        tasks.append({"task_id": listed.task_id, "status": status, "title": listed.title})
    return {
        "account": student.account,
        "name": student.name,
        "class_id": student.class_id,
        "message": "",
        "tasks": tasks,
    }


def _document(item) -> dict:
    labels = {"queued": "排队中", "ready": "可用", "failed": "失败"}
    status = getattr(item, "status", "")
    return {
        "doc_id": item.doc_id,
        "name": item.name,
        "status": labels.get(status, ""),
        "detail": getattr(item, "detail", ""),
    }


def _account_rows(room) -> list:
    rows = []
    for item in room.roster.classes():
        for student in room.roster.students(item.class_id):
            rows.append({
                "account": student.account,
                "name": student.name,
                "class_id": student.class_id,
                "class_name": item.name,
            })
    return rows


def _student_task(page, task_id: str) -> dict:
    session = page.sessions.get(task_id)
    if session is None:
        work = page.catalog.work(task_id)
        return {
            "task_id": task_id,
            "title": page.catalog.get(task_id).title,
            "status": "待办",
            "locked": False,
            "send_closed": False,
            "questions": [_live_question(question, answer, None) for question, answer in zip(work.questions, work.answers)],
            "presets": [],
            "scaffold": None,
            "dialogue": [_turn(turn) for turn in work.dialogue],
        }
    view = session.view()
    revealed = view.revealed
    return {
        "task_id": task_id,
        "title": page.catalog.get(task_id).title,
        "status": view.status,
        "locked": view.answers_locked,
        "send_closed": view.send_closed,
        "questions": [
            _live_question(question, answer, revealed[index] if revealed else None)
            for index, (question, answer) in enumerate(zip(session.work.questions, session.work.answers))
        ],
        "presets": list(view.presets),
        "scaffold": None if view.scaffold is None else _scaffold(view.scaffold),
        "dialogue": [_turn(turn) for turn in view.dialogue],
    }


def _live_question(question, answer, revealed) -> dict:
    payload = {
        "prompt": question.prompt,
        "text": answer.text,
        "selected": list(answer.selected),
    }
    if isinstance(question, ChoiceQuestion):
        payload["kind"] = question.selection.value
        payload["choices"] = list(question.choices)
        payload["requirements"] = ""
    elif isinstance(question, TrueFalseQuestion):
        payload["kind"] = "判断"
        payload["choices"] = ["正确", "错误"]
        payload["requirements"] = ""
    else:
        payload["kind"] = "综合"
        payload["choices"] = []
        payload["requirements"] = question.requirements
    if revealed is not None:
        shown = revealed.answer if isinstance(revealed.answer, str) else "、".join(revealed.answer)
        payload["reference"] = shown
        payload["explanation"] = revealed.explanation
    return payload


def _scaffold(scaffold) -> dict:
    return {
        "text": scaffold.text,
        "assets": [{"kind": asset.kind.value, "filename": asset.filename} for asset in scaffold.assets],
    }


def _turn(turn) -> dict:
    return {
        "question": turn.question,
        "scaffold": None if turn.scaffold is None else _scaffold(turn.scaffold),
    }
