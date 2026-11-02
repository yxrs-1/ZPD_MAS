import { useEffect, useRef, useState, type RefObject } from 'react'

function Pupil({
  size = 12,
  maxDistance = 5,
  pupilColor = 'black',
  forceLookX,
  forceLookY,
  mouseX,
  mouseY,
}: {
  size?: number
  maxDistance?: number
  pupilColor?: string
  forceLookX?: number
  forceLookY?: number
  mouseX: number
  mouseY: number
}) {
  const pupilRef = useRef<HTMLDivElement>(null)
  const position = pupilPosition(pupilRef, mouseX, mouseY, maxDistance, forceLookX, forceLookY)
  return (
    <div
      ref={pupilRef}
      className="rounded-full"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        backgroundColor: pupilColor,
        transform: `translate(${position.x}px, ${position.y}px)`,
        transition: 'transform 0.1s ease-out',
      }}
    />
  )
}

function EyeBall({
  size = 48,
  pupilSize = 16,
  maxDistance = 10,
  eyeColor = 'white',
  pupilColor = 'black',
  isBlinking = false,
  forceLookX,
  forceLookY,
  mouseX,
  mouseY,
}: {
  size?: number
  pupilSize?: number
  maxDistance?: number
  eyeColor?: string
  pupilColor?: string
  isBlinking?: boolean
  forceLookX?: number
  forceLookY?: number
  mouseX: number
  mouseY: number
}) {
  const eyeRef = useRef<HTMLDivElement>(null)
  const position = pupilPosition(eyeRef, mouseX, mouseY, maxDistance, forceLookX, forceLookY)
  return (
    <div
      ref={eyeRef}
      className="flex items-center justify-center overflow-hidden rounded-full transition-all duration-150"
      style={{
        width: `${size}px`,
        height: isBlinking ? '2px' : `${size}px`,
        backgroundColor: eyeColor,
      }}
    >
      {!isBlinking ? (
        <div
          className="rounded-full"
          style={{
            width: `${pupilSize}px`,
            height: `${pupilSize}px`,
            backgroundColor: pupilColor,
            transform: `translate(${position.x}px, ${position.y}px)`,
            transition: 'transform 0.1s ease-out',
          }}
        />
      ) : null}
    </div>
  )
}

function pupilPosition(
  ref: RefObject<HTMLDivElement | null>,
  mouseX: number,
  mouseY: number,
  maxDistance: number,
  forceLookX?: number,
  forceLookY?: number,
) {
  if (forceLookX !== undefined && forceLookY !== undefined) return { x: forceLookX, y: forceLookY }
  const node = ref.current
  if (!node) return { x: 0, y: 0 }
  const box = node.getBoundingClientRect()
  const deltaX = mouseX - (box.left + box.width / 2)
  const deltaY = mouseY - (box.top + box.height / 2)
  const distance = Math.min(Math.hypot(deltaX, deltaY), maxDistance)
  const angle = Math.atan2(deltaY, deltaX)
  return { x: Math.cos(angle) * distance, y: Math.sin(angle) * distance }
}

export function Characters({
  isTyping = false,
  showPassword = false,
  passwordLength = 0,
}: {
  isTyping?: boolean
  showPassword?: boolean
  passwordLength?: number
}) {
  const [mouseX, setMouseX] = useState(() => window.innerWidth / 2)
  const [mouseY, setMouseY] = useState(() => window.innerHeight / 2)
  const [purpleBlinking, setPurpleBlinking] = useState(false)
  const [blackBlinking, setBlackBlinking] = useState(false)
  const [lookingAtEachOther, setLookingAtEachOther] = useState(false)
  const [purplePeeking, setPurplePeeking] = useState(false)
  const purpleRef = useRef<HTMLDivElement>(null)
  const blackRef = useRef<HTMLDivElement>(null)
  const yellowRef = useRef<HTMLDivElement>(null)
  const orangeRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const look = (event: MouseEvent) => {
      setMouseX(event.clientX)
      setMouseY(event.clientY)
    }
    window.addEventListener('mousemove', look)
    return () => window.removeEventListener('mousemove', look)
  }, [])

  useEffect(() => blinkLoop(setPurpleBlinking), [])
  useEffect(() => blinkLoop(setBlackBlinking), [])

  useEffect(() => {
    if (!isTyping) {
      setLookingAtEachOther(false)
      return
    }
    setLookingAtEachOther(true)
    const timer = window.setTimeout(() => setLookingAtEachOther(false), 800)
    return () => window.clearTimeout(timer)
  }, [isTyping])

  useEffect(() => {
    if (passwordLength === 0 || !showPassword) {
      setPurplePeeking(false)
      return
    }
    let inner = 0
    const outer = window.setTimeout(() => {
      setPurplePeeking(true)
      inner = window.setTimeout(() => setPurplePeeking(false), 800)
    }, Math.random() * 3000 + 2000)
    return () => {
      window.clearTimeout(outer)
      window.clearTimeout(inner)
    }
  }, [passwordLength, showPassword, purplePeeking])

  const purplePos = bodyPosition(purpleRef, mouseX, mouseY)
  const blackPos = bodyPosition(blackRef, mouseX, mouseY)
  const yellowPos = bodyPosition(yellowRef, mouseX, mouseY)
  const orangePos = bodyPosition(orangeRef, mouseX, mouseY)
  const hidingPassword = passwordLength > 0 && !showPassword
  const passwordVisible = passwordLength > 0 && showPassword
  const eyes = { mouseX, mouseY }

  return (
    <div className="characters" aria-hidden="true">
      <img className="logo" src="/static/logo.png" alt="" />
      <div className="cast-slot">
      <div className="cast">
        <div ref={purpleRef} className="absolute bottom-0 transition-all duration-700 ease-in-out" style={{
          left: '70px', width: '180px', height: isTyping || hidingPassword ? '440px' : '400px',
          backgroundColor: '#6C3FF5', borderRadius: '10px 10px 0 0', zIndex: 1, transformOrigin: 'bottom center',
          transform: passwordVisible ? 'skewX(0deg)' : isTyping || hidingPassword
            ? `skewX(${purplePos.bodySkew - 12}deg) translateX(40px)`
            : `skewX(${purplePos.bodySkew}deg)`,
        }}>
          <div className="absolute flex gap-8 transition-all duration-700 ease-in-out" style={{
            left: passwordVisible ? '20px' : lookingAtEachOther ? '55px' : `${45 + purplePos.faceX}px`,
            top: passwordVisible ? '35px' : lookingAtEachOther ? '65px' : `${40 + purplePos.faceY}px`,
          }}>
            <EyeBall size={18} pupilSize={7} maxDistance={5} pupilColor="#2D2D2D" isBlinking={purpleBlinking} {...eyes}
              forceLookX={passwordVisible ? (purplePeeking ? 4 : -4) : lookingAtEachOther ? 3 : undefined}
              forceLookY={passwordVisible ? (purplePeeking ? 5 : -4) : lookingAtEachOther ? 4 : undefined} />
            <EyeBall size={18} pupilSize={7} maxDistance={5} pupilColor="#2D2D2D" isBlinking={purpleBlinking} {...eyes}
              forceLookX={passwordVisible ? (purplePeeking ? 4 : -4) : lookingAtEachOther ? 3 : undefined}
              forceLookY={passwordVisible ? (purplePeeking ? 5 : -4) : lookingAtEachOther ? 4 : undefined} />
          </div>
        </div>
        <div ref={blackRef} className="absolute bottom-0 transition-all duration-700 ease-in-out" style={{
          left: '240px', width: '120px', height: '310px', backgroundColor: '#2D2D2D',
          borderRadius: '8px 8px 0 0', zIndex: 2, transformOrigin: 'bottom center',
          transform: passwordVisible ? 'skewX(0deg)' : lookingAtEachOther
            ? `skewX(${blackPos.bodySkew * 1.5 + 10}deg) translateX(20px)`
            : isTyping || hidingPassword
              ? `skewX(${blackPos.bodySkew * 1.5}deg)`
              : `skewX(${blackPos.bodySkew}deg)`,
        }}>
          <div className="absolute flex gap-6 transition-all duration-700 ease-in-out" style={{
            left: passwordVisible ? '10px' : lookingAtEachOther ? '32px' : `${26 + blackPos.faceX}px`,
            top: passwordVisible ? '28px' : lookingAtEachOther ? '12px' : `${32 + blackPos.faceY}px`,
          }}>
            <EyeBall size={16} pupilSize={6} maxDistance={4} pupilColor="#2D2D2D" isBlinking={blackBlinking} {...eyes}
              forceLookX={passwordVisible ? -4 : lookingAtEachOther ? 0 : undefined}
              forceLookY={passwordVisible ? -4 : lookingAtEachOther ? -4 : undefined} />
            <EyeBall size={16} pupilSize={6} maxDistance={4} pupilColor="#2D2D2D" isBlinking={blackBlinking} {...eyes}
              forceLookX={passwordVisible ? -4 : lookingAtEachOther ? 0 : undefined}
              forceLookY={passwordVisible ? -4 : lookingAtEachOther ? -4 : undefined} />
          </div>
        </div>
        <div ref={orangeRef} className="absolute bottom-0 transition-all duration-700 ease-in-out" style={{
          left: '0px', width: '240px', height: '200px', zIndex: 3, backgroundColor: '#FF9B6B',
          borderRadius: '120px 120px 0 0', transformOrigin: 'bottom center',
          transform: passwordVisible ? 'skewX(0deg)' : `skewX(${orangePos.bodySkew}deg)`,
        }}>
          <div className="absolute flex gap-8 transition-all duration-200 ease-out" style={{
            left: passwordVisible ? '50px' : `${82 + orangePos.faceX}px`,
            top: passwordVisible ? '85px' : `${90 + orangePos.faceY}px`,
          }}>
            <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D" {...eyes}
              forceLookX={passwordVisible ? -5 : undefined} forceLookY={passwordVisible ? -4 : undefined} />
            <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D" {...eyes}
              forceLookX={passwordVisible ? -5 : undefined} forceLookY={passwordVisible ? -4 : undefined} />
          </div>
        </div>
        <div ref={yellowRef} className="absolute bottom-0 transition-all duration-700 ease-in-out" style={{
          left: '310px', width: '140px', height: '230px', backgroundColor: '#E8D754',
          borderRadius: '70px 70px 0 0', zIndex: 4, transformOrigin: 'bottom center',
          transform: passwordVisible ? 'skewX(0deg)' : `skewX(${yellowPos.bodySkew}deg)`,
        }}>
          <div className="absolute flex gap-6 transition-all duration-200 ease-out" style={{
            left: passwordVisible ? '20px' : `${52 + yellowPos.faceX}px`,
            top: passwordVisible ? '35px' : `${40 + yellowPos.faceY}px`,
          }}>
            <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D" {...eyes}
              forceLookX={passwordVisible ? -5 : undefined} forceLookY={passwordVisible ? -4 : undefined} />
            <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D" {...eyes}
              forceLookX={passwordVisible ? -5 : undefined} forceLookY={passwordVisible ? -4 : undefined} />
          </div>
          <div className="absolute h-[4px] w-20 rounded-full bg-[#2D2D2D] transition-all duration-200 ease-out" style={{
            left: passwordVisible ? '10px' : `${40 + yellowPos.faceX}px`,
            top: passwordVisible ? '88px' : `${88 + yellowPos.faceY}px`,
          }} />
        </div>
      </div>
      </div>
    </div>
  )
}

function blinkLoop(setBlinking: (value: boolean) => void) {
  let outer = 0
  let inner = 0
  let cancelled = false
  const schedule = () => {
    outer = window.setTimeout(() => {
      if (cancelled) return
      setBlinking(true)
      inner = window.setTimeout(() => {
        if (cancelled) return
        setBlinking(false)
        schedule()
      }, 150)
    }, Math.random() * 4000 + 3000)
  }
  schedule()
  return () => {
    cancelled = true
    window.clearTimeout(outer)
    window.clearTimeout(inner)
  }
}

function bodyPosition(ref: RefObject<HTMLDivElement | null>, mouseX: number, mouseY: number) {
  const node = ref.current
  if (!node) return { faceX: 0, faceY: 0, bodySkew: 0 }
  const rect = node.getBoundingClientRect()
  const deltaX = mouseX - (rect.left + rect.width / 2)
  const deltaY = mouseY - (rect.top + rect.height / 3)
  return {
    faceX: Math.max(-15, Math.min(15, deltaX / 20)),
    faceY: Math.max(-10, Math.min(10, deltaY / 30)),
    bodySkew: Math.max(-6, Math.min(6, -deltaX / 120)),
  }
}
