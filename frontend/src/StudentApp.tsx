import { useEffect, useRef, useState, type FormEvent, type MouseEvent, type ReactNode } from 'react'
import { api, type ScaffoldView, type StudentQuestion, type StudentTask, type TaskSummary } from './api'
import { go } from './path'

const imageName = /\.(png|jpe?g|gif|webp|svg)$/i

export function StudentApp({ path }: { path: string }) {
  const parts = path.split('/').filter(Boolean)
  const [name, setName] = useState('')
  const [open, setOpen] = useState(false)
  const panel = useRef<HTMLDivElement>(null)
  useEffect(() => {
    api.me('学生').then((me) => {
      if (me.role !== '学生') go('/')
      else setName(me.name || me.account || '')
    })
  }, [])
  useEffect(() => { setOpen(false) }, [path])
  useEffect(() => {
    if (!open) return
    function onPointer(event: PointerEvent) {
      const target = event.target
      if (target instanceof Node && panel.current?.contains(target)) return
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

  const taskId = parts[1] === 'tasks' && parts[2] ? decodeURIComponent(parts[2]) : ''
  if (taskId) return <Work id={taskId} />

  return (
    <div className="desk">
      <nav className="rail">
        <img className="mark" src="/static/logo.png" alt="" />
        <a href="/student" onClick={sameTab} className="is-current" aria-current="page">待办</a>
        <div className="rail-account" ref={panel}>
          <button className="account" type="button" onClick={() => setOpen(!open)}>
            {name || '账号'}
          </button>
          {open ? (
            <button className="quiet" type="button" onClick={async () => {
              await api.logout('学生')
              go('/')
            }}>退出</button>
          ) : null}
        </div>
      </nav>
      <div className="stage">
        <div key={path} className="sheet">
          <Todo />
        </div>
      </div>
    </div>
  )
}

function Todo() {
  const [tasks, setTasks] = useState<TaskSummary[] | null>(null)
  useEffect(() => {
    api.studentTasks().then((result) => setTasks(result.tasks)).catch(() => go('/'))
  }, [])
  return (
    <>
      <h1>待办</h1>
      <p className="job">教师布置的任务。</p>
      {tasks && tasks.length === 0 ? <p className="empty">还没有任务。教师布置之后会出现在这里。</p> : null}
      {tasks && tasks.length > 0 ? (
        <ul className="rows">
          {tasks.map((task) => (
            <li key={task.task_id}>
              <a href={'/student/tasks/' + task.task_id} onClick={sameTab}>{task.title || task.task_id}</a>
              <Badge status={task.status} />
            </li>
          ))}
        </ul>
      ) : null}
    </>
  )
}

function Work({ id }: { id: string }) {
  const [task, setTask] = useState<StudentTask | null>(null)
  const [own, setOwn] = useState('')
  const [pending, setPending] = useState('')
  const [flying, setFlying] = useState('')
  const [reveal, setReveal] = useState(-1)
  const [live, setLive] = useState<LiveReply | null>(null)
  const [pane, setPane] = useState<'答疑' | '结构图'>('答疑')
  const ready = useRef<StudentTask | null>(null)
  const askSource = useRef('')
  const logRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    api.studentTask(id).then(setTask).catch(() => go('/student'))
  }, [id])
  useEffect(() => {
    const node = logRef.current
    if (!node) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    node.scrollTo({ top: node.scrollHeight, behavior: reduce ? 'auto' : 'smooth' })
  }, [task?.dialogue.length, flying, reveal, live?.shown, live?.kind])
  useEffect(() => {
    if (!live) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduce && live.shown !== live.received) {
      setLive({ ...live, shown: live.received })
      return
    }
    if (live.shown.length < live.received.length) {
      const timer = window.setTimeout(() => {
        setLive((current) => current ? { ...current, shown: current.received.slice(0, current.shown.length + 1) } : current)
      }, 28)
      return () => window.clearTimeout(timer)
    }
    const next = ready.current
    if (!live.done || !next) return
    ready.current = null
    setReveal(next.dialogue.length - 1)
    setTask(next)
    if (askSource.current === '自己写的') setOwn('')
    setPending('')
    setFlying('')
    setLive(null)
  }, [live])
  if (!task) return null

  function update(index: number, patch: Partial<StudentQuestion>) {
    setTask({
      ...task!,
      questions: task!.questions.map((question, item) => item === index ? { ...question, ...patch } : question),
    })
  }

  async function save(event: FormEvent) {
    event.preventDefault()
    if (pending) return
    setPending('保存')
    try {
      setTask(await api.saveAnswers(id, task!.questions.map((question) => (
        question.kind === '综合' ? { text: question.text } : { selected: question.selected }
      ))))
    } finally {
      setPending('')
    }
  }

  async function ask(question: string, source: string) {
    const text = question.trim()
    if (text === '' || pending) return
    setPane('答疑')
    askSource.current = source
    ready.current = null
    setPending(source === '预设提问' ? '提问:' + question : '提问')
    setFlying(text)
    setLive({ received: '', shown: '', kind: '', done: false })
    try {
      await api.askStream(id, text, source, {
        onKind: (kind) => setLive((current) => current ? { ...current, kind } : current),
        onText: (reply) => setLive((current) => current ? { ...current, received: reply } : current),
        onTask: (next) => {
          ready.current = next
          setLive((current) => current ? { ...current, done: true } : current)
        },
      })
    } catch {
      ready.current = null
      setLive(null)
      try {
        setTask(await api.studentTask(id))
      } catch {
        go('/student')
      }
    } finally {
      if (!ready.current) {
        setPending('')
        setFlying('')
        setLive(null)
      }
    }
  }

  async function submit() {
    if (pending) return
    if (!window.confirm('提交之后不能再改，也不能再提问。')) return
    setPending('提交')
    try {
      setTask(await api.submit(id))
    } finally {
      setPending('')
    }
  }

  const done = task.questions.filter(answered).length
  const total = task.questions.length
  const pictures = figures(task)
  return (
    <div className="desk answer">
      <section className="answer-card">
        <header className="answer-head">
          <a className="back" href="/student" onClick={sameTab}>待办</a>
          <div className="answer-title-row">
            <h1>{task.title || task.task_id}</h1>
            <p className="progress-label"><b>{done}/{total}</b> 题已作答</p>
          </div>
          <div className="meter" role="progressbar" aria-valuenow={done} aria-valuemin={0} aria-valuemax={total} aria-label="已作答">
            <span style={{ width: total === 0 ? '0%' : (done / total * 100) + '%' }} />
          </div>
        </header>
        <form id="answers" className="answer-scroll" onSubmit={save}>
          {task.questions.map((question, index) => (
            <section key={index} className="qcard">
              <div className="qhead">
                <span className="qno">{String(index + 1).padStart(2, '0')}</span>
                <span className="kind">{question.kind}</span>
                <span className={answered(question) ? 'qstate on' : 'qstate'}>{answered(question) ? '已作答' : '待作答'}</span>
              </div>
              <Stem prompt={question.prompt} />
              {question.requirements ? <p className="job">{question.requirements}</p> : null}
              {question.kind === '综合' ? (
                <textarea
                  className="area"
                  value={question.text}
                  disabled={task.locked}
                  onChange={(event) => update(index, { text: event.target.value })}
                />
              ) : (
                <div className={question.choices.every((choice) => choice.trim().length <= 18) ? 'picks compact' : 'picks'}>
                  {question.choices.map((choice) => (
                    <label key={choice} className={'pick' + (question.selected.includes(choice) ? ' on' : '')}>
                      <input
                        type={question.kind === '多选' ? 'checkbox' : 'radio'}
                        name={'q' + index}
                        checked={question.selected.includes(choice)}
                        disabled={task.locked}
                        onChange={() => update(index, {
                          selected: question.kind === '多选' ? flip(question.selected, choice) : [choice],
                        })}
                      />
                      <span>{choice}</span>
                    </label>
                  ))}
                </div>
              )}
              {question.reference !== undefined ? (
                <div className="result">
                  <p className="stem">参考答案：{question.reference}</p>
                  <p className="stem">解析：{question.explanation}</p>
                </div>
              ) : null}
            </section>
          ))}
        </form>
        <footer className="answer-foot">
          <p>{task.locked ? '已经提交。' : '做完再提交。'}</p>
          <div>
            {!task.locked ? (
              <button className="line" type="submit" form="answers" disabled={pending !== ''}>
                {pending === '保存' ? '正在保存' : '保存作答'}
              </button>
            ) : null}
            {!task.send_closed ? (
              <button className="primary" type="button" disabled={pending !== ''} onClick={submit}>
                {pending === '提交' ? '正在提交' : '提交'}
              </button>
            ) : null}
          </div>
        </footer>
      </section>
      <section className="answer-card agent" aria-label="支架智能体">
        <header className="agent-head">
          <div className="agent-id">
            <img src="/static/logo.png" alt="" />
            <div>
              <p className="who-title">支架智能体</p>
              <p className="agent-role">问你想清楚的，而不是给出答案</p>
            </div>
          </div>
          <div className="panes" role="tablist">
            <button type="button" role="tab" aria-selected={pane === '答疑'} className={pane === '答疑' ? 'on' : ''} onClick={() => setPane('答疑')}>智能答疑</button>
            <button type="button" role="tab" aria-selected={pane === '结构图'} className={pane === '结构图' ? 'on' : ''} onClick={() => setPane('结构图')}>结构图</button>
          </div>
          <p className="linked">已关联当前练习 · {task.title || task.task_id}</p>
        </header>
        {pane === '答疑' ? (
          <div className="log" ref={logRef}>
            {task.dialogue.length === 0 && task.scaffold ? (
              <Scaffold taskId={id} scaffold={task.scaffold} />
            ) : null}
            {task.dialogue.map((turn, index) => (
              <div key={index}>
                <article className="msg student">
                  <div>
                    <p className="who-me">我</p>
                    <div className="bubble">{turn.question}</div>
                  </div>
                </article>
                {turn.scaffold ? (
                  <Scaffold taskId={id} scaffold={turn.scaffold} turn={index} reveal={index === reveal} />
                ) : null}
              </div>
            ))}
            {flying ? (
              <article className="msg student">
                <div>
                  <p className="who-me">我</p>
                  <div className="bubble lift">{flying}</div>
                </div>
              </article>
            ) : null}
            {live ? <LiveScaffold live={live} /> : null}
          </div>
        ) : (
          <div className="gallery">
            {pictures.length === 0 ? <p className="empty">还没有结构图</p> : pictures.map((picture) => (
              <FigurePlate
                key={(picture.turn ?? 'open') + picture.filename}
                taskId={id}
                kind={picture.kind}
                filename={picture.filename}
                turn={picture.turn}
                reveal={false}
              />
            ))}
          </div>
        )}
        {!task.send_closed ? (
          <div className="ask-stack">
            {pane === '答疑' && task.presets.slice(0, 2).length > 0 ? (
              <div className="ask-presets">
                {task.presets.slice(0, 2).map((preset) => (
                  <button
                    key={preset}
                    className="chip"
                    type="button"
                    title={preset}
                    disabled={pending !== ''}
                    onClick={() => ask(preset, '预设提问')}
                  >
                    {pending === '提问:' + preset ? '正在提问' : preset}
                  </button>
                ))}
              </div>
            ) : null}
            <form className="askbar" onSubmit={(event) => {
              event.preventDefault()
              ask(own, '自己写的')
            }}>
              <textarea
                className="ask-input"
                value={own}
                aria-label="提问"
                placeholder="输入你的问题，一起拆解思路…"
                rows={2}
                onChange={(event) => setOwn(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    ask(own, '自己写的')
                  }
                }}
              />
              <button className="send" type="submit" aria-label={pending === '提问' ? '正在提问' : '提问'} disabled={pending !== ''}>
                <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
                  <path d="M8 2.2 13.2 8H10v5.3H6V8H2.8L8 2.2Z" fill="currentColor" />
                </svg>
              </button>
            </form>
            <p className="ask-note">Enter 发送 · 回答仅供参考，请结合题目自己想</p>
          </div>
        ) : null}
      </section>
    </div>
  )
}

type LiveReply = { received: string; shown: string; kind: string; done: boolean }

function LiveScaffold({ live }: { live: LiveReply }) {
  return (
    <article className="msg agent" aria-busy="true">
      <div className="reply">
        <p className="agent-name">支架智能体</p>
        <div className="bubble writing">
          {live.shown ? (
            <p className="stem">{live.shown}<span className="caret" aria-hidden="true" /></p>
          ) : (
            <p className="stem dots" aria-label="正在写"><i /><i /><i /></p>
          )}
        </div>
        {live.kind ? (
          <div className="plate plate-wait" aria-label={'正在准备' + live.kind}>
            <span className="ink-line" />
            <span className="ink-line short" />
            <span className="plate-kind">正在准备{live.kind}</span>
          </div>
        ) : null}
      </div>
    </article>
  )
}

function Scaffold({
  taskId,
  scaffold,
  turn,
  reveal = false,
}: {
  taskId: string
  scaffold: ScaffoldView
  turn?: number
  reveal?: boolean
}) {
  const pictures = scaffold.assets.filter((asset) => imageName.test(asset.filename))
  const files = scaffold.assets.filter((asset) => !imageName.test(asset.filename))
  return (
    <article className="msg agent">
      <div className="reply">
        <p className="agent-name">支架智能体</p>
        {scaffold.text ? (
          <div className={'bubble' + (reveal ? ' scaffold-in' : '')}>
            <p className="stem">{scaffold.text}</p>
          </div>
        ) : null}
        {pictures.map((asset) => (
          <FigurePlate
            key={asset.filename}
            taskId={taskId}
            kind={asset.kind}
            filename={asset.filename}
            turn={turn}
            reveal={reveal}
          />
        ))}
        {files.map((asset) => (
          <FileLink key={asset.filename} taskId={taskId} kind={asset.kind} filename={asset.filename} turn={turn} />
        ))}
      </div>
    </article>
  )
}

function assetSrc(taskId: string, filename: string, turn?: number) {
  return turn === undefined
    ? '/api/student/tasks/' + encodeURIComponent(taskId) + '/assets/' + encodeURIComponent(filename)
    : '/api/student/tasks/' + encodeURIComponent(taskId) + '/turns/' + turn + '/assets/' + encodeURIComponent(filename)
}

function FigurePlate({
  taskId,
  kind,
  filename,
  turn,
  reveal,
}: {
  taskId: string
  kind: string
  filename: string
  turn?: number
  reveal: boolean
}) {
  const src = assetSrc(taskId, filename, turn)
  const opener = useRef<HTMLButtonElement>(null)
  const closer = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  function close() {
    setOpen(false)
    opener.current?.focus()
  }
  useEffect(() => {
    if (!open) return
    closer.current?.focus()
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') close()
      if (event.key === 'Tab') {
        event.preventDefault()
        closer.current?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])
  return (
    <>
      <button
        ref={opener}
        type="button"
        className={'plate' + (reveal ? ' figure-in' : '')}
        aria-label={'放大' + kind}
        onClick={() => setOpen(true)}
      >
        <span className="plate-kind">{kind}</span>
        <img src={src} alt="" />
      </button>
      {open ? (
        <div className="viewer" role="dialog" aria-modal="true" aria-label={'放大' + kind} onClick={close}>
          <div className="viewer-frame" onClick={(event) => event.stopPropagation()}>
            <button ref={closer} type="button" className="line" onClick={close}>关闭</button>
            <div className="viewer-scroll">
              <img src={src} alt={kind} />
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}

function FileLink({
  taskId,
  kind,
  filename,
  turn,
}: {
  taskId: string
  kind: string
  filename: string
  turn?: number
}) {
  const src = assetSrc(taskId, filename, turn)
  return (
    <p className="file">
      {kind} {filename} <a href={src} download={filename}>保存</a>
    </p>
  )
}

function Badge({ status }: { status: string }) {
  const tone = status === '已完成' ? 'done' : status === '待办' ? 'work' : ''
  return <span className={'badge ' + tone}>{status}</span>
}

function Stem({ prompt }: { prompt: string }) {
  const parts = splitStem(prompt)
  return (
    <>
      <p className="stem">{parts.lead}</p>
      {parts.code ? <CodeBlock code={parts.code} /> : null}
    </>
  )
}

function splitStem(prompt: string) {
  const lines = prompt.split('\n')
  const at = lines.findIndex((line, index) => index > 0 && looksLikeCode(line))
  if (at < 0) return { lead: prompt, code: '' }
  return { lead: lines.slice(0, at).join('\n').trim(), code: lines.slice(at).join('\n').trimEnd() }
}

function looksLikeCode(line: string) {
  return /^\s*(#|for |while |if |elif |else:|def |import |return |class |print\(|[A-Za-z_]\w*\s*=)/.test(line)
}

const codeWord = /(#.*$)|(\b(?:for|while|if|elif|else|def|return|import|in|and|or|not|break|continue|class|range)\b)|("(?:\\.|[^"])*"|'(?:\\.|[^'])*')|(\b\d+\b)/g

function highlight(line: string) {
  const nodes: ReactNode[] = []
  let last = 0
  for (const match of line.matchAll(codeWord)) {
    const index = match.index ?? 0
    if (index > last) nodes.push(line.slice(last, index))
    const text = match[0]
    const tone = match[1] ? 'note' : match[2] ? 'key' : match[3] ? 'str' : 'num'
    nodes.push(<em key={index} className={tone}>{text}</em>)
    last = index + text.length
  }
  if (last < line.length) nodes.push(line.slice(last))
  return nodes
}

function CodeBlock({ code }: { code: string }) {
  return (
    <div className="code">
      {code.split('\n').map((line, index) => (
        <div className="code-line" key={index}>
          <i>{index + 1}</i>
          <span>{highlight(line)}</span>
        </div>
      ))}
    </div>
  )
}

function answered(question: StudentQuestion) {
  return question.kind === '综合' ? question.text.trim() !== '' : question.selected.length > 0
}

function figures(task: StudentTask) {
  const rows: { kind: string; filename: string; turn?: number }[] = []
  for (const asset of task.scaffold?.assets || []) {
    if (imageName.test(asset.filename)) rows.push(asset)
  }
  task.dialogue.forEach((turn, index) => {
    for (const asset of turn.scaffold?.assets || []) {
      if (imageName.test(asset.filename)) rows.push({ ...asset, turn: index })
    }
  })
  return rows
}

function flip(selected: string[], choice: string) {
  return selected.includes(choice) ? selected.filter((item) => item !== choice) : selected.concat(choice)
}

function sameTab(event: MouseEvent<HTMLAnchorElement>) {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
  event.preventDefault()
  go(event.currentTarget.getAttribute('href') || '/')
}
