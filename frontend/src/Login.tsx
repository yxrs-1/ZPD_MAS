import { useEffect, useState, type FormEvent } from 'react'
import { api, type Role } from './api'
import { Characters } from './Characters'
import { go } from './path'

export function Login({ role, notice }: { role: Role; notice: string }) {
  const [account, setAccount] = useState('')
  const [password, setPassword] = useState('')
  const [shown, setShown] = useState(false)
  const [typing, setTyping] = useState(false)
  const [message, setMessage] = useState(notice)
  const [open, setOpen] = useState(false)
  const [menu, setMenu] = useState(false)

  useEffect(() => {
    if (open) {
      setMenu(true)
      return
    }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setMenu(false)
      return
    }
    const timer = window.setTimeout(() => setMenu(false), 180)
    return () => window.clearTimeout(timer)
  }, [open])

  useEffect(() => {
    setMessage(notice)
    setAccount('')
    setPassword('')
    setTyping(false)
  }, [role, notice])

  async function submit(event: FormEvent) {
    event.preventDefault()
    const result = await api.login({ role, account, password })
    if (!result.ok) {
      setMessage(result.message || '账号或密码不正确')
      return
    }
    go(role === '教师' ? '/teacher' : '/student')
  }

  return (
    <main className="entrance">
      <Characters isTyping={typing} showPassword={shown} passwordLength={password.length} />
      <section className="panel">
        <h1>登录</h1>
        <p className="sub">请填写账号和密码</p>
        {message ? <p className="notice">{message}</p> : null}
        <form onSubmit={submit}>
          <div className="field">
            身份
            <span className={'picker' + (open ? ' open' : '')}>
              <button type="button" className="picker-face" aria-expanded={open} onClick={() => setOpen(!open)}>
                <span key={role} className="picker-value">{role}</span>
              </button>
              {menu ? (
                <ul className={'picker-menu' + (open ? '' : ' closing')} role="listbox">
                  {(['学生', '教师'] as Role[]).map((item) => (
                    <li
                      key={item}
                      role="option"
                      aria-selected={item === role}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={(event) => {
                        event.preventDefault()
                        event.stopPropagation()
                        setOpen(false)
                        if (item !== role) go(item === '教师' ? '/teacher/login' : '/')
                      }}
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              ) : null}
            </span>
          </div>
          <label className="field">
            账号
            <input
              name="account"
              value={account}
              autoComplete="username"
              onFocus={() => setTyping(true)}
              onBlur={() => setTyping(false)}
              onChange={(event) => setAccount(event.target.value)}
            />
          </label>
          <label className="field">
            密码
            <span className="secret">
              <input
                name="password"
                type={shown ? 'text' : 'password'}
                value={password}
                autoComplete="current-password"
                onChange={(event) => setPassword(event.target.value)}
              />
              <button type="button" onClick={() => setShown(!shown)}>{shown ? '隐藏' : '显示'}</button>
            </span>
          </label>
          <button type="submit">登录</button>
        </form>
        <p className={'links' + (role === '学生' ? ' in' : '')} inert={role === '学生' ? undefined : true}>
          <span>
            <a href="/student/register" onClick={(event) => { event.preventDefault(); go('/student/register') }}>注册账号</a>
            <a href="/?forgot=1" onClick={(event) => { event.preventDefault(); go('/?forgot=1') }}>忘记密码</a>
          </span>
        </p>
      </section>
    </main>
  )
}

export function Register() {
  const [classes, setClasses] = useState<{ class_id: string; name: string }[]>([])
  const [classId, setClassId] = useState('')
  const [account, setAccount] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [shown, setShown] = useState(false)
  const [message, setMessage] = useState('')
  const [typing, setTyping] = useState(false)

  useEffect(() => {
    api.classes().then((result) => setClasses(result.classes))
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    const result = await api.register({ account, password, name, class_id: classId })
    if (!result.ok) {
      setMessage(result.message || '')
      return
    }
    go('/student')
  }

  return (
    <main className="entrance">
      <Characters isTyping={typing} showPassword={shown} passwordLength={password.length} />
      <section className="panel">
        <h1>注册</h1>
        <p className="sub">加入已经建好的班级</p>
        {message ? <p className="notice">{message}</p> : null}
        <form onSubmit={submit}>
          <label className="field">
            账号
            <input value={account} onFocus={() => setTyping(true)} onBlur={() => setTyping(false)} onChange={(event) => setAccount(event.target.value)} />
          </label>
          <label className="field">
            密码
            <span className="secret">
              <input
                type={shown ? 'text' : 'password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              <button type="button" onClick={() => setShown(!shown)}>{shown ? '隐藏' : '显示'}</button>
            </span>
          </label>
          <label className="field">
            姓名
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label className="field">
            班级
            <select value={classId} onChange={(event) => setClassId(event.target.value)}>
              <option value="">选择班级</option>
              {classes.map((item) => <option key={item.class_id} value={item.class_id}>{item.name}</option>)}
            </select>
          </label>
          <button type="submit">注册</button>
        </form>
      </section>
    </main>
  )
}
