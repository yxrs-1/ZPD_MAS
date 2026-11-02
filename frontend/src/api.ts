export type Role = '教师' | '学生'

export type Me = {
  ok: boolean
  role?: Role | ''
  account?: string
  name?: string
  message?: string
}

async function send(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(path, { ...init, headers, credentials: 'include' })
  const raw = await response.text()
  let data: any
  try {
    data = raw ? JSON.parse(raw) : {}
  } catch {
    throw new Error('没有收到结果，请再试一次')
  }
  if (response.status === 401) {
    throw new Error(data.message || '请先登录')
  }
  return data
}

async function streamAsk(
  id: string,
  question: string,
  source: string,
  handlers: {
    onKind: (kind: string) => void
    onText: (text: string) => void
    onTask: (task: StudentTask) => void
  },
) {
  const response = await fetch('/api/student/tasks/' + id + '/ask', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ question, source }),
  })
  if (response.status === 401) throw new Error('请先登录')
  if (!response.ok || !response.body) throw new Error('没有收到结果，请再试一次')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finished = false
  while (!finished) {
    const chunk = await reader.read()
    if (chunk.done) break
    buffer += decoder.decode(chunk.value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''
    for (const part of parts) {
      let event = 'message'
      const data: string[] = []
      for (const line of part.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        if (line.startsWith('data:')) data.push(line.slice(5).trim())
      }
      if (data.length === 0) continue
      const payload = JSON.parse(data.join('\n'))
      if (event === 'kind') handlers.onKind(payload)
      if (event === 'text') handlers.onText(payload)
      if (event === 'task') {
        finished = true
        handlers.onTask(payload)
      }
      if (event === 'error') throw new Error(typeof payload === 'string' ? payload : '没有收到结果，请再试一次')
    }
  }
  if (!finished) throw new Error('没有收到结果，请再试一次')
}

export const api = {
  me: (role?: Role) => send('/api/me' + (role ? '?role=' + encodeURIComponent(role) : '')) as Promise<Me>,
  login: (body: { role: Role; account: string; password: string }) =>
    send('/api/login', { method: 'POST', body: JSON.stringify(body) }) as Promise<Me>,
  logout: (role?: Role) => send('/api/logout', { method: 'POST', body: JSON.stringify({ role: role || '' }) }),
  classes: () => send('/api/classes') as Promise<{ classes: ClassItem[] }>,
  register: (body: { account: string; password: string; name: string; class_id: string }) =>
    send('/api/register', { method: 'POST', body: JSON.stringify(body) }) as Promise<Me>,
  teacherTasks: () => send('/api/teacher/tasks') as Promise<{ account: string; tasks: TaskSummary[] }>,
  createTask: () => send('/api/teacher/tasks', { method: 'POST' }) as Promise<TeacherTask>,
  teacherTask: (id: string) => send('/api/teacher/tasks/' + id) as Promise<TeacherTask>,
  updateTask: (id: string, body: object) =>
    send('/api/teacher/tasks/' + id, { method: 'POST', body: JSON.stringify(body) }) as Promise<TeacherTask & { deleted?: boolean }>,
  objectives: (body: { text: string; objectives?: string; action?: string }) =>
    send('/api/teacher/objectives', { method: 'POST', body: JSON.stringify(body) }),
  teacherClasses: () => send('/api/teacher/classes') as Promise<{ classes: ClassItem[] }>,
  createClass: (name: string) =>
    send('/api/teacher/classes', { method: 'POST', body: JSON.stringify({ name }) }),
  teacherClass: (id: string) => send('/api/teacher/classes/' + id) as Promise<ClassDetail>,
  classAction: (id: string, action: string) =>
    send('/api/teacher/classes/' + id, { method: 'POST', body: JSON.stringify({ action }) }),
  importClass: (id: string, file: File) => {
    const body = new FormData()
    body.append('file', file)
    return send('/api/teacher/classes/' + id + '/import', { method: 'POST', body }) as Promise<ClassDetail>
  },
  teacherStudent: (classId: string, account: string) =>
    send('/api/teacher/classes/' + classId + '/students/' + account) as Promise<StudentDetail>,
  studentAction: (classId: string, account: string, body: object) =>
    send('/api/teacher/classes/' + classId + '/students/' + account, { method: 'POST', body: JSON.stringify(body) }),
  documents: () => send('/api/teacher/documents') as Promise<{ documents: DocumentItem[]; message?: string }>,
  uploadDocument: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return send('/api/teacher/documents', { method: 'POST', body }) as Promise<{ documents: DocumentItem[]; message: string }>
  },
  deleteDocument: (id: string) =>
    send('/api/teacher/documents/' + id + '/delete', { method: 'POST' }) as Promise<{ documents: DocumentItem[]; message: string }>,
  accounts: () => send('/api/teacher/accounts') as Promise<Accounts>,
  accountAction: (body: object) =>
    send('/api/teacher/accounts', { method: 'POST', body: JSON.stringify(body) }) as Promise<Accounts>,
  password: (body: { old_password: string; password: string }) =>
    send('/api/teacher/password', { method: 'POST', body: JSON.stringify(body) }) as Promise<{ message: string }>,
  studentTasks: () => send('/api/student/tasks') as Promise<{ account: string; name: string; tasks: TaskSummary[] }>,
  studentTask: (id: string) => send('/api/student/tasks/' + id) as Promise<StudentTask>,
  saveAnswers: (id: string, answers: { text?: string; selected?: string[] }[]) =>
    send('/api/student/tasks/' + id + '/answers', { method: 'POST', body: JSON.stringify({ answers }) }) as Promise<StudentTask>,
  ask: (id: string, question: string, source: string) =>
    send('/api/student/tasks/' + id + '/ask', { method: 'POST', body: JSON.stringify({ question, source }) }) as Promise<StudentTask>,
  askStream: (
    id: string,
    question: string,
    source: string,
    handlers: {
      onKind: (kind: string) => void
      onText: (text: string) => void
      onTask: (task: StudentTask) => void
    },
  ) => streamAsk(id, question, source, handlers),
  submit: (id: string) =>
    send('/api/student/tasks/' + id + '/submit', { method: 'POST' }) as Promise<StudentTask>,
}

export type ClassItem = { class_id: string; name: string }
export type TaskSummary = { task_id: string; status: string; title?: string }
export type DraftQuestion = {
  kind: string
  prompt: string
  options: string[]
  requirements: string
  selected: string[]
  answer: string
  explanation: string
}
export type TeacherTask = {
  task_id: string
  title: string
  status: string
  message: string
  editable: boolean
  has_draft: boolean
  published: boolean
  questions: DraftQuestion[]
  classes: { class_id: string; name: string; assigned: boolean }[]
}
export type ClassDetail = {
  class_id: string
  name: string
  message: string
  failures: { row: number; reason: string }[]
  students: { account: string; name: string }[]
}
export type StudentDetail = {
  account: string
  name: string
  class_id: string
  message: string
  tasks: TaskSummary[]
}
export type DocumentItem = { doc_id: string; name: string; status: string; detail: string }
export type Accounts = {
  students: { account: string; name: string; class_id: string; class_name: string }[]
  classes: ClassItem[]
  message: string
}
export type StudentQuestion = {
  kind: string
  prompt: string
  choices: string[]
  requirements: string
  text: string
  selected: string[]
  reference?: string
  explanation?: string
}
export type ScaffoldView = { text: string; assets: { kind: string; filename: string }[] }
export type StudentTask = {
  task_id: string
  title?: string
  status: string
  locked: boolean
  send_closed: boolean
  questions: StudentQuestion[]
  presets: string[]
  scaffold: ScaffoldView | null
  dialogue: { question: string; scaffold: ScaffoldView | null }[]
}
