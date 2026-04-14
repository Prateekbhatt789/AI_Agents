const baseProps = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
}

function Icon({ children, className = 'h-4 w-4', viewBox = '0 0 24 24' }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox={viewBox}
      {...baseProps}
    >
      {children}
    </svg>
  )
}

export function SearchIcon(props) {
  return (
    <Icon {...props}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="M16 16l4 4" />
    </Icon>
  )
}

export function TargetIcon(props) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="7" />
      <circle cx="12" cy="12" r="2.5" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
    </Icon>
  )
}

export function SparklesIcon(props) {
  return (
    <Icon {...props}>
      <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3Z" />
      <path d="M5 16l.8 2.2L8 19l-2.2.8L5 22l-.8-2.2L2 19l2.2-.8L5 16Z" />
      <path d="M19 14l.9 2.6L22.5 18l-2.6.9L19 21.5l-.9-2.6L15.5 18l2.6-.9L19 14Z" />
    </Icon>
  )
}

export function ChartIcon(props) {
  return (
    <Icon {...props}>
      <path d="M4 19h16" />
      <path d="M7 16v-4" />
      <path d="M12 16V8" />
      <path d="M17 16v-6" />
    </Icon>
  )
}

export function PinIcon(props) {
  return (
    <Icon {...props}>
      <path d="M12 21s6-4.8 6-10a6 6 0 1 0-12 0c0 5.2 6 10 6 10Z" />
      <circle cx="12" cy="11" r="2.5" />
    </Icon>
  )
}

export function DownloadIcon(props) {
  return (
    <Icon {...props}>
      <path d="M12 4v10" />
      <path d="M8.5 10.5 12 14l3.5-3.5" />
      <path d="M5 19h14" />
    </Icon>
  )
}

export function HospitalIcon(props) {
  return (
    <Icon {...props}>
      <path d="M6 20V8l3-2 3 2 3-2 3 2v12" />
      <path d="M10 13h4" />
      <path d="M12 11v4" />
      <path d="M9 20v-3h6v3" />
    </Icon>
  )
}

export function PawIcon(props) {
  return (
    <Icon {...props}>
      <circle cx="8" cy="8" r="1.5" />
      <circle cx="16" cy="8" r="1.5" />
      <circle cx="6" cy="12" r="1.5" />
      <circle cx="18" cy="12" r="1.5" />
      <path d="M12 17c-2.5 0-4.5 1.3-4.5 3h9c0-1.7-2-3-4.5-3Z" />
    </Icon>
  )
}

export function BusIcon(props) {
  return (
    <Icon {...props}>
      <rect x="6" y="4" width="12" height="12" rx="2" />
      <path d="M6 9h12" />
      <path d="M9 16v3M15 16v3" />
      <circle cx="9" cy="19" r="1" />
      <circle cx="15" cy="19" r="1" />
    </Icon>
  )
}

export function FuelIcon(props) {
  return (
    <Icon {...props}>
      <path d="M7 19V6.5A1.5 1.5 0 0 1 8.5 5h5A1.5 1.5 0 0 1 15 6.5V19" />
      <path d="M7 10h8" />
      <path d="M15 8h1.5l1.5 2v6a1 1 0 0 1-2 0v-3" />
    </Icon>
  )
}

export function SchoolIcon(props) {
  return (
    <Icon {...props}>
      <path d="M3 10 12 5l9 5-9 5-9-5Z" />
      <path d="M7 12.5V17c0 1.2 2.2 2.5 5 2.5s5-1.3 5-2.5v-4.5" />
    </Icon>
  )
}

export function UtensilsIcon(props) {
  return (
    <Icon {...props}>
      <path d="M6 3v8" />
      <path d="M4 3v4a2 2 0 0 0 4 0V3" />
      <path d="M6 11v10" />
      <path d="M14 3v18" />
      <path d="M14 3c2.5 0 4 2 4 4.5S16.5 12 14 12" />
    </Icon>
  )
}

export function PillIcon(props) {
  return (
    <Icon {...props}>
      <path d="M9.5 6.5a4.2 4.2 0 0 1 6 6l-4.8 4.8a4.2 4.2 0 1 1-6-6l4.8-4.8Z" />
      <path d="M8.5 15.5 15.5 8.5" />
    </Icon>
  )
}

export function BuildingIcon(props) {
  return (
    <Icon {...props}>
      <path d="M5 20V6l7-3 7 3v14" />
      <path d="M9 10h.01M15 10h.01M9 14h.01M15 14h.01" />
      <path d="M11 20v-3h2v3" />
    </Icon>
  )
}

export function BotIcon(props) {
  return (
    <Icon {...props}>
      <rect x="6" y="8" width="12" height="10" rx="3" />
      <path d="M12 4v4" />
      <circle cx="9.5" cy="13" r="1" />
      <circle cx="14.5" cy="13" r="1" />
      <path d="M10 16h4" />
    </Icon>
  )
}

export function SendIcon(props) {
  return (
    <Icon {...props}>
      <path d="M21 3 10 14" />
      <path d="m21 3-7 18-4-7-7-4 18-7Z" />
    </Icon>
  )
}

export function GlobeIcon(props) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3a14.5 14.5 0 0 1 0 18a14.5 14.5 0 0 1 0-18Z" />
    </Icon>
  )
}

export function LoaderIcon(props) {
  return (
    <Icon {...props}>
      <path d="M12 3a9 9 0 1 0 9 9" />
    </Icon>
  )
}
