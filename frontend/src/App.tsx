import { Login, Register } from './Login'
import { StudentApp } from './StudentApp'
import { TeacherApp } from './TeacherApp'
import { usePath } from './path'
import type { Role } from './api'

export default function App() {
  const path = usePath()
  const route = path.split('?')[0]
  const forgot = new URLSearchParams(path.split('?')[1] || '').get('forgot') === '1'
  if (route === '/student/register') return <Register />
  if (route === '/' || route === '/login' || route === '/student/login') {
    return <Login role="学生" notice={forgot ? '请教师重置密码' : ''} />
  }
  if (route === '/teacher/login') return <Login role="教师" notice="" />
  if (route.startsWith('/teacher')) return <TeacherApp path={route} />
  if (route.startsWith('/student')) return <StudentApp path={route} />
  return <Login role={'学生' as Role} notice="" />
}
