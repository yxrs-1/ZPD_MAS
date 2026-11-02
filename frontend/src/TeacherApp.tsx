import { createContext, useContext, useEffect, useRef, useState, type FormEvent, type MouseEvent, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import {
  api,
  type Accounts,
  type ClassDetail,
  type DocumentItem,
  type DraftQuestion,
  type StudentDetail,
  type TaskSummary,
  type TeacherTask,
} from './api'
import { go } from './path'

const kinds = ['单选', '多选', '判断', '综合']
const StageSlot = createContext<HTMLElement | null>(null)

export function TeacherApp({ path }: { path: string }) {
  const [account, setAccount] = useState('')
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [slot, setSlot] = useState<HTMLDivElement | null>(null)
  const accountAct = useFlag()
  const accountPanel = useRef<HTMLDivElement>(null)
  const current = path.startsWith('/teacher/classes')
    ? '班级'
    : path.startsWith('/teacher/documents')
      ? '资料库'
      : path.startsWith('/teacher/accounts')
        ? '账号管理'
        : '任务'

  useEffect(() => {
    api.me('教师').then((me) => {
      if (me.role !== '教师') go('/teacher/login')
      else setAccount(me.account || '')
    })
  }, [])

  useEffect(() => {
    setOpen(false)
  }, [path])

  useEffect(() => {
    if (!open) return
    function onPointer(event: PointerEvent) {
      const target = event.target
      if (target instanceof Node && accountPanel.current?.contains(target)) return
      setOpen(false)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div className="desk">
      <nav className="rail">
        <img className="mark" src="/static/logo.png" alt="" />
        <NavLink href="/teacher" current={current === '任务'}>任务</NavLink>
        <NavLink href="/teacher/classes" current={current === '班级'}>班级</NavLink>
        <NavLink href="/teacher/documents" current={current === '资料库'}>资料库</NavLink>
        <NavLink href="/teacher/accounts" current={current === '账号管理'}>账号管理</NavLink>
        <div className="rail-account" ref={accountPanel}>
          <button className="account" type="button" onClick={() => setOpen(!open)}>
          {account || '账号'}
        </button>
        {open ? (
          <form
              className="account-form"
            onSubmit={(event) => {
              event.preventDefault()
              const form = new FormData(event.currentTarget)
              void accountAct.run('修改密码', async () => {
                const result = await api.password({
                  old_password: String(form.get('old_password') || ''),
                  password: String(form.get('password') || ''),
                })
                setMessage(result.message)
                if (result.message === '密码已修改') {
                  setOpen(false)
                  go('/teacher')
                }
              })
            }}
          >
              <input className="field" name="old_password" type="password" placeholder="原密码" disabled={accountAct.key !== ''} />
              <input className="field" name="password" type="password" placeholder="新密码" disabled={accountAct.key !== ''} />
              <Act name="修改密码" pending={accountAct.key} shown={accountAct.shown} className="primary" type="submit">修改密码</Act>
            <Act
                name="退出"
                pending={accountAct.key}
                shown={accountAct.shown}
                className="quiet"
                onClick={() => {
                  void accountAct.run('退出', async () => {
                    await api.logout('教师')
                    go('/teacher/login')
                  })
                }}
            >
              退出
            </Act>
          </form>
        ) : null}
        </div>
      </nav>
      <div className="stage" ref={setSlot}>
        <StageSlot.Provider value={slot}>
        {message && path === '/teacher' ? <p className="flash">{message}</p> : null}
        <div key={path} className="sheet">
        <TeacherPage path={path} />
        </div>
        </StageSlot.Provider>
      </div>
    </div>
  )
}

function TeacherPage({ path }: { path: string }) {
  const parts = path.split('/').filter(Boolean)
  if (parts.length === 1) return <TaskList />
  if (parts[1] === 'tasks' && parts[2] === 'new') return <NewTask />
  if (parts[1] === 'tasks' && parts[2]) return <TaskEditor id={decodeURIComponent(parts[2])} />
  if (parts[1] === 'objectives') return <Objectives />
  if (parts[1] === 'classes' && parts[3] === 'students' && parts[4]) {
    return <ClassStudent classId={decodeURIComponent(parts[2])} account={decodeURIComponent(parts[4])} />
  }
  if (parts[1] === 'classes' && parts[2]) return <ClassPage id={decodeURIComponent(parts[2])} />
  if (parts[1] === 'classes') return <ClassList />
  if (parts[1] === 'documents') return <Documents />
  if (parts[1] === 'accounts') return <AccountPage />
  return <TaskList />
}

function TaskList() {
  const [tasks, setTasks] = useState<TaskSummary[] | null>(null)
  useEffect(() => {
    api.teacherTasks().then((result) => setTasks(result.tasks)).catch(() => go('/teacher/login'))
  }, [])
  return (
    <>
      <header className="sheet-head">
        <div>
          <h1>任务列表</h1>
        </div>
        <button className="primary" type="button" onClick={() => go('/teacher/tasks/new')}>新建</button>
      </header>
      {tasks && tasks.length === 0 ? <p className="empty">还没有任务</p> : null}
      {tasks && tasks.length > 0 ? (
        <ul className="rows">
          {tasks.map((task) => (
            <li key={task.task_id}>
              <a href={'/teacher/tasks/' + task.task_id} onClick={link}>{task.title || task.task_id}</a>
              <Badge status={task.status} />
            </li>
          ))}
        </ul>
      ) : null}
    </>
  )
}

function NewTask() {
  const { key, shown, run } = useFlag()
  return (
    <>
      <Back href="/teacher" />
      <h1>新建任务</h1>
      <div className="choices">
        <button
          className={'choice' + (key ? ' is-hold' : '') + (shown ? ' busy' : '')}
          type="button"
          disabled={key !== ''}
          aria-busy={key !== '' || undefined}
          onClick={() => {
            void run('手动添加', async () => {
              const task = await api.createTask()
              go('/teacher/tasks/' + task.task_id)
            })
          }}
        >
          <strong>手动添加</strong>
          <span>从一道空题开始</span>
        </button>
        <a className="choice" href="/teacher/objectives" onClick={link}>
          <strong>智能体生成</strong>
          <span>写出需求，确认目标后再出题</span>
        </a>
      </div>
    </>
  )
}

function TaskEditor({ id }: { id: string }) {
  const [task, setTask] = useState<TeacherTask | null>(null)
  const [name, setName] = useState('')
  const slot = useContext(StageSlot)
  const { key, shown, run } = useFlag()
  useEffect(() => {
    api.teacherTask(id).then((next) => {
      setTask(next)
      setName(next.title || next.task_id)
    }).catch(() => go('/teacher'))
  }, [id])
  if (!task) return null

  async function send(action: string, questions = task!.questions, classIds?: string[]) {
    await run(action, async () => {
      const next = await api.updateTask(id, { action, questions, class_ids: classIds })
      if (next.deleted) {
        go('/teacher')
        return
      }
      setTask(next)
    })
  }

  async function rename() {
    const nextName = name.trim()
    const current = task!.title || task!.task_id
    if (nextName === '') {
      setName(current)
      setTask({ ...task!, message: '先填写任务名称' })
      return
    }
    if (nextName === current) return
    const next = await api.updateTask(id, { action: '改名', title: nextName, questions: [] })
    if (next.deleted) return
    setTask(next)
    setName(next.title || next.task_id)
  }

  return (
    <>
      <Back href="/teacher" />
      <header className="sheet-head">
        <div>
          <input
            className="task-name"
            aria-label="任务名称"
            value={name}
            onChange={(event) => setName(event.target.value)}
            onBlur={() => { void rename() }}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                event.currentTarget.blur()
              }
            }}
          />
        </div>
        <Badge status={task.status} />
      </header>
      {task.message ? <p className="note">{task.message}</p> : null}
      {task.questions.map((question, index) => (
        <QuestionCard
          key={index}
          question={question}
          index={index}
          count={task.questions.length}
          locked={!task.editable}
          onChange={(next) => {
            const questions = task.questions.slice()
            questions[index] = next
            setTask({ ...task, questions })
          }}
          onAction={(action) => send(action)}
          pending={key}
          shown={shown}
        />
      ))}
      {task.editable ? (
        <Dock slot={slot}>
          {kinds.map((kind) => (
            <Act key={kind} name={'add:' + kind} pending={key} shown={shown} className="line" onClick={() => send('add:' + kind)}>增加{kind}</Act>
          ))}
          <Act name="save" pending={key} shown={shown} className={task.has_draft || task.questions.length === 0 ? 'primary' : 'line'} onClick={() => send('save')}>保存</Act>
          {task.has_draft ? <Act name="abandon" pending={key} shown={shown} className="line" onClick={() => send('abandon')}>放弃草稿</Act> : null}
          {!task.has_draft && task.questions.length > 0 ? (
            <Act name="publish" pending={key} shown={shown} className="primary" onClick={() => send('publish')}>发布</Act>
          ) : null}
          <Act name="delete" pending={key} shown={shown} className="danger" onClick={() => send('delete')}>删除</Act>
        </Dock>
      ) : (
        <Act name="delete" pending={key} shown={shown} className="danger" onClick={() => send('delete')}>删除</Act>
      )}
      {task.published ? (
        <form
          className="assign"
          onSubmit={(event) => {
            event.preventDefault()
            const picked = [...new FormData(event.currentTarget).getAll('class_id')].map(String)
            send('布置', task.questions, picked)
          }}
        >
          {task.classes.map((item) => (
            <label key={item.class_id}>
              <input type="checkbox" name="class_id" value={item.class_id} defaultChecked={item.assigned} />
              {item.name}
            </label>
          ))}
          <Act name="布置" pending={key} shown={shown} className="primary" type="submit">布置</Act>
        </form>
      ) : null}
    </>
  )
}

function Dock({ slot, children }: { slot: HTMLElement | null; children: ReactNode }) {
  if (!slot) return null
  return createPortal(<div className="dock">{children}</div>, slot)
}

function QuestionCard({
  question,
  index,
  count,
  locked,
  onChange,
  onAction,
  pending,
  shown,
}: {
  question: DraftQuestion
  index: number
  count: number
  locked: boolean
  onChange: (question: DraftQuestion) => void
  onAction: (action: string) => void
  pending: string
  shown: string
}) {
  return (
    <section className="question">
      <p className="kind">{question.kind}</p>
      <input
        className="prompt"
        value={question.prompt}
        placeholder="题目"
        disabled={locked}
        onChange={(event) => onChange({ ...question, prompt: event.target.value })}
      />
      {question.kind === '单选' || question.kind === '多选' ? (
        <>
          {question.options.map((option, optionIndex) => (
            <div key={optionIndex} className="option-row">
              <input
                type={question.kind === '单选' ? 'radio' : 'checkbox'}
                checked={question.selected.includes(option)}
                disabled={locked}
                onChange={() => onChange({ ...question, selected: toggle(question, option) })}
              />
              <input
                className="option-line"
                value={option}
                placeholder="选项"
                disabled={locked}
                onChange={(event) => {
                  const options = question.options.slice()
                  const previous = options[optionIndex]
                  options[optionIndex] = event.target.value
                  onChange({
                    ...question,
                    options,
                    selected: question.selected.map((item) => item === previous ? event.target.value : item),
                  })
                }}
              />
              {!locked && optionIndex > 0 ? <Act name={'up-option:' + index + ':' + optionIndex} pending={pending} shown={shown} className="quiet" onClick={() => onAction('up-option:' + index + ':' + optionIndex)}>上移选项</Act> : null}
              {!locked && optionIndex < question.options.length - 1 ? <Act name={'down-option:' + index + ':' + optionIndex} pending={pending} shown={shown} className="quiet" onClick={() => onAction('down-option:' + index + ':' + optionIndex)}>下移选项</Act> : null}
              {!locked ? <Act name={'delete-option:' + index + ':' + optionIndex} pending={pending} shown={shown} className="quiet" onClick={() => onAction('delete-option:' + index + ':' + optionIndex)}>删除选项</Act> : null}
            </div>
          ))}
          {!locked ? <Act name={'add-option:' + index} pending={pending} shown={shown} className="quiet" onClick={() => onAction('add-option:' + index)}>增加选项</Act> : null}
        </>
      ) : null}
      {question.kind === '判断' ? (
        <div className="judge">
          {['正确', '错误'].map((choice) => (
            <label key={choice}>
              <input
                type="radio"
                checked={question.selected.includes(choice)}
                disabled={locked}
                onChange={() => onChange({ ...question, selected: [choice] })}
              />
              {choice}
            </label>
          ))}
        </div>
      ) : null}
      {question.kind === '综合' ? (
        <>
          <input className="subline" placeholder="作答要求" value={question.requirements} disabled={locked} onChange={(event) => onChange({ ...question, requirements: event.target.value })} />
          <input className="subline" placeholder="参考答案" value={question.answer} disabled={locked} onChange={(event) => onChange({ ...question, answer: event.target.value })} />
        </>
      ) : null}
      <input className="subline" placeholder="解析" value={question.explanation} disabled={locked} onChange={(event) => onChange({ ...question, explanation: event.target.value })} />
      {!locked ? (
        <div className="question-tools">
          <Act name={'delete:' + index} pending={pending} shown={shown} className="quiet" onClick={() => onAction('delete:' + index)}>删除题目</Act>
          {index > 0 ? <Act name={'up:' + index} pending={pending} shown={shown} className="quiet" onClick={() => onAction('up:' + index)}>上移</Act> : null}
          {index < count - 1 ? <Act name={'down:' + index} pending={pending} shown={shown} className="quiet" onClick={() => onAction('down:' + index)}>下移</Act> : null}
        </div>
      ) : null}
    </section>
  )
}

function Objectives() {
  const [text, setText] = useState('')
  const [objectives, setObjectives] = useState('')
  const [message, setMessage] = useState('')
  const { key, shown, run } = useFlag()
  function submit(action: string) {
    return (event: FormEvent) => {
      event.preventDefault()
      void run(action, async () => {
        const result = await api.objectives({ text, objectives, action })
        setMessage(result.message || '')
        if (result.task_id) go('/teacher/tasks/' + result.task_id)
        if (result.text !== undefined) setText(result.text)
        if (result.objectives !== undefined) setObjectives(result.objectives)
      }, true)
    }
  }
  const hold = key !== ''
  return (
    <>
      <Back href="/teacher/tasks/new" />
      <h1>目标</h1>
      {message ? <p className="note">{message}</p> : null}
      <form className="stack" onSubmit={submit('生成目标')}>
        <textarea className="area" name="text" value={text} placeholder="要练什么" disabled={hold} onChange={(event) => setText(event.target.value)} />
        {key === '生成目标' ? <Writing label="正在生成目标" /> : null}
        <Act name="生成目标" pending={key} shown={shown} className="primary" type="submit" agent label="正在生成目标">生成目标</Act>
      </form>
      {objectives ? (
        <form className="stack" onSubmit={submit('确认')}>
          <textarea className="area" value={objectives} disabled={hold} onChange={(event) => setObjectives(event.target.value)} />
          {key === '确认' ? <Writing label="正在出题" /> : null}
          <Act name="确认" pending={key} shown={shown} className="primary" type="submit" agent label="正在出题">确认</Act>
        </form>
      ) : null}
    </>
  )
}

function ClassList() {
  const [classes, setClasses] = useState<{ class_id: string; name: string }[]>([])
  const [name, setName] = useState('')
  const [message, setMessage] = useState('')
  const { key, shown, run } = useFlag()
  useEffect(() => { api.teacherClasses().then((result) => setClasses(result.classes)) }, [])
  return (
    <>
      <h1>班级</h1>
      {message ? <p className="note">{message}</p> : null}
      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault()
          void run('创建', async () => {
            const result = await api.createClass(name)
            if (!result.ok) {
              setMessage(result.message || '')
              setClasses(result.classes || classes)
              return
            }
            go('/teacher/classes/' + result.class_id)
          })
        }}
      >
        <input className="field" value={name} placeholder="班级名称" disabled={key !== ''} onChange={(event) => setName(event.target.value)} />
        <Act name="创建" pending={key} shown={shown} className="primary" type="submit">创建</Act>
      </form>
      {classes.length > 0 ? (
        <ul className="rows">
          {classes.map((item) => (
            <li key={item.class_id}>
              <a href={'/teacher/classes/' + item.class_id} onClick={link}>{item.name}</a>
            </li>
          ))}
        </ul>
      ) : <p className="empty">还没有班级</p>}
    </>
  )
}

function ClassPage({ id }: { id: string }) {
  const [detail, setDetail] = useState<ClassDetail | null>(null)
  const { key, shown, run } = useFlag()
  useEffect(() => { api.teacherClass(id).then(setDetail).catch(() => go('/teacher/classes')) }, [id])
  if (!detail) return null
  return (
    <>
      <Back href="/teacher/classes" />
      <h1>{detail.name}</h1>
      {detail.message ? <p className="note">{detail.message}</p> : null}
      {detail.failures.length > 0 ? (
        <ul className="warn">
          {detail.failures.map((item) => <li key={item.row}>第{item.row}行：{item.reason}</li>)}
        </ul>
      ) : null}
      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault()
          const file = new FormData(event.currentTarget).get('file')
          if (!(file instanceof File)) return
          void run('导入', async () => {
            setDetail(await api.importClass(id, file))
          })
        }}
      >
        <input name="file" type="file" disabled={key !== ''} />
        <Act name="导入" pending={key} shown={shown} className="primary" type="submit">导入</Act>
      </form>
      {detail.students.length > 0 ? (
        <ul className="rows">
          {detail.students.map((student) => (
            <li key={student.account}>
              <a href={'/teacher/classes/' + id + '/students/' + student.account} onClick={link}>{student.name}</a>
              <span className="meta">{student.account}</span>
            </li>
          ))}
        </ul>
      ) : <p className="empty">还没有学生</p>}
      <p>
      <Act
          name="删除班级"
          pending={key}
          shown={shown}
          className="danger"
          onClick={() => {
            void run('删除班级', async () => {
              await api.classAction(id, '删除班级')
              go('/teacher/classes')
            })
          }}
      >
        删除班级
      </Act>
      </p>
    </>
  )
}

function ClassStudent({ classId, account }: { classId: string; account: string }) {
  const [detail, setDetail] = useState<StudentDetail | null>(null)
  const { key, shown, run } = useFlag()
  useEffect(() => { api.teacherStudent(classId, account).then(setDetail).catch(() => go('/teacher/classes/' + classId)) }, [classId, account])
  if (!detail) return null
  return (
    <>
      <Back href={'/teacher/classes/' + classId} />
      <h1>{detail.name}</h1>
      <p className="job">{detail.account}</p>
      {detail.message ? <p className="note">{detail.message}</p> : null}
      <form className="composer" onSubmit={(event) => {
        event.preventDefault()
        const name = String(new FormData(event.currentTarget).get('name') || '')
        void run('修改姓名', async () => {
          setDetail(await api.studentAction(classId, account, { action: '修改姓名', name }))
        })
      }}>
        <input className="field" name="name" placeholder="姓名" disabled={key !== ''} />
        <Act name="修改姓名" pending={key} shown={shown} className="primary" type="submit">修改姓名</Act>
      </form>
      <form className="composer" onSubmit={(event) => {
        event.preventDefault()
        const password = String(new FormData(event.currentTarget).get('password') || '')
        void run('重置密码', async () => {
          setDetail(await api.studentAction(classId, account, { action: '重置密码', password }))
        })
      }}>
        <input className="field" name="password" type="password" placeholder="新密码" disabled={key !== ''} />
        <Act name="重置密码" pending={key} shown={shown} className="primary" type="submit">重置密码</Act>
      </form>
      <Act name="移除" pending={key} shown={shown} className="danger" onClick={() => {
        void run('移除', async () => {
          await api.studentAction(classId, account, { action: '移除' })
          go('/teacher/classes/' + classId)
        })
      }}>移除</Act>
      <ul className="rows">
        {detail.tasks.map((task) => (
          <li key={task.task_id}>
            <span>{task.title || task.task_id}</span>
            <Badge status={task.status} />
          </li>
        ))}
      </ul>
    </>
  )
}

function Documents() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [message, setMessage] = useState('')
  const { key, shown, run } = useFlag()
  async function load() {
    const result = await api.documents()
    setDocuments(result.documents)
    if (result.message) setMessage(result.message)
  }
  useEffect(() => { load() }, [])
  useEffect(() => {
    if (!documents.some((item) => item.status === '排队中')) return
    const timer = window.setTimeout(load, 3000)
    return () => window.clearTimeout(timer)
  }, [documents])
  return (
    <>
      <h1>资料库</h1>
      {message ? <p className="note">{message}</p> : null}
      <form className="composer" onSubmit={(event) => {
        event.preventDefault()
        const file = new FormData(event.currentTarget).get('file')
        if (!(file instanceof File) || file.name === '') return
        void run('上传', async () => {
          const result = await api.uploadDocument(file)
          setMessage(result.message)
          setDocuments(result.documents)
        })
      }}>
        <input name="file" type="file" accept=".docx,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf" disabled={key !== ''} />
        <Act name="上传" pending={key} shown={shown} className="primary" type="submit">上传</Act>
      </form>
      {documents.length > 0 ? (
        <ul className="rows">
          {documents.map((item) => (
            <li key={item.doc_id}>
              <span>{item.name}</span>
              {item.status ? <Badge status={item.status} detail={item.detail} /> : null}
              <Act name={'删除:' + item.doc_id} pending={key} shown={shown} className="danger" onClick={() => {
                void run('删除:' + item.doc_id, async () => {
                  const result = await api.deleteDocument(item.doc_id)
                  setMessage(result.message)
                  setDocuments(result.documents)
                })
              }}>删除</Act>
            </li>
          ))}
        </ul>
      ) : <p className="empty">还没有资料</p>}
    </>
  )
}

function AccountPage() {
  const [data, setData] = useState<Accounts | null>(null)
  const { key, shown, run } = useFlag()
  useEffect(() => { api.accounts().then(setData) }, [])
  if (!data) return <h1>账号管理</h1>
  return (
    <>
      <h1>账号管理</h1>
      {data.message ? <p className="note">{data.message}</p> : null}
      {data.students.length > 0 ? (
        <ul className="records">
          {data.students.map((student) => (
            <li key={student.account} className="record">
              <div className="who">
                <strong>{student.name}</strong>
                <span className="meta">{student.account}</span>
                <em>{student.class_name}</em>
              </div>
              <form onSubmit={(event) => {
                event.preventDefault()
                const password = String(new FormData(event.currentTarget).get('password') || '')
                void run('重置:' + student.account, async () => {
                  setData(await api.accountAction({ action: '重置密码', account: student.account, password }))
                })
              }}>
                <input className="field" name="password" type="password" placeholder="新密码" disabled={key !== ''} />
                <Act name={'重置:' + student.account} pending={key} shown={shown} className="line" type="submit">重置密码</Act>
              </form>
              <form onSubmit={(event) => {
                event.preventDefault()
                const classId = String(new FormData(event.currentTarget).get('class_id') || '')
                void run('换班:' + student.account, async () => {
                  setData(await api.accountAction({ action: '换班', account: student.account, class_id: classId }))
                })
              }}>
                <select className="field" name="class_id" defaultValue={student.class_id} disabled={key !== ''}>
                  {data.classes.map((item) => <option key={item.class_id} value={item.class_id}>{item.name}</option>)}
                </select>
                <Act name={'换班:' + student.account} pending={key} shown={shown} className="line" type="submit">换班</Act>
              </form>
            </li>
          ))}
        </ul>
      ) : <p className="empty">还没有学生</p>}
    </>
  )
}

function Back({ href }: { href: string }) {
  return <a className="back" href={href} onClick={sameTab}>返回</a>
}

function NavLink({ href, current, children }: { href: string; current: boolean; children: string }) {
  return (
    <a href={href} onClick={link} className={current ? 'is-current' : undefined} aria-current={current ? 'page' : undefined}>
      {children}
    </a>
  )
}

function Badge({ status, detail }: { status: string; detail?: string }) {
  const tone = status === '已开始' || status === '排队中' ? 'work'
    : status === '已完成' ? 'done'
    : status === '已发布' || status === '可用' ? 'ready'
    : status === '失败' ? 'bad'
    : ''
  return <span className={'badge ' + tone + (status === '排队中' ? ' wait' : '')}>{status}{detail ? ' ' + detail : ''}</span>
}

function toggle(question: DraftQuestion, option: string) {
  if (question.kind === '单选') return [option]
  return question.selected.includes(option)
    ? question.selected.filter((item) => item !== option)
    : question.selected.concat(option)
}

function useFlag() {
  const [key, setKey] = useState('')
  const [shown, setShown] = useState('')
  const lock = useRef(false)
  useEffect(() => {
    if (!key) return
    const timer = window.setTimeout(() => setShown(key), 180)
    return () => window.clearTimeout(timer)
  }, [key])
  async function run(name: string, work: () => Promise<void>, immediate = false) {
    if (lock.current) return
    lock.current = true
    setKey(name)
    if (immediate) setShown(name)
    try {
      await work()
    } finally {
      lock.current = false
      setKey('')
      setShown('')
    }
  }
  return { key, shown, run }
}

function Act({
  name,
  pending,
  shown,
  className,
  type = 'button',
  agent = false,
  label,
  children,
  onClick,
}: {
  name: string
  pending: string
  shown: string
  className: string
  type?: 'button' | 'submit'
  agent?: boolean
  label?: string
  children: ReactNode
  onClick?: () => void
}) {
  const on = pending === name
  return (
    <button
      className={className + (on ? ' is-hold' : '') + ((agent ? on : shown === name) ? ' busy' : '')}
      type={type}
      disabled={pending !== ''}
      aria-busy={on || undefined}
      aria-label={on && label ? label : undefined}
      onClick={onClick}
    >
      {children}
      {agent && on ? <span className="dots" aria-hidden="true"><i /><i /><i /></span> : null}
    </button>
  )
}

function Writing({ label }: { label: string }) {
  return (
    <div className="writing-pad" role="status">
      <span className="ink-line" />
      <span className="ink-line short" />
      <p className="sr-only">{label}</p>
    </div>
  )
}

function link(event: { preventDefault: () => void; currentTarget: { getAttribute: (name: string) => string | null } }) {
  event.preventDefault()
  go(event.currentTarget.getAttribute('href') || '/')
}

function sameTab(event: MouseEvent<HTMLAnchorElement>) {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
  event.preventDefault()
  go(event.currentTarget.getAttribute('href') || '/')
}
