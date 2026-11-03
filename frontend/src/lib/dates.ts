// The backend always sends UTC. Everything is shown in Argentina's local time, 24-hour clock.

const TIME_ZONE = "America/Argentina/Buenos_Aires";

const TIME = new Intl.DateTimeFormat("es-AR", { timeZone: TIME_ZONE, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const DATE_TIME = new Intl.DateTimeFormat("es-AR", {
  timeZone: TIME_ZONE, day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});

// "2026-11-03T15:05:00Z" -> Date. A value without zone is taken as UTC (that is what the backend stores).
export function parseUtc(iso: string): Date {
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
  return new Date(hasZone ? iso : `${iso}Z`);
}

export function formatTime(iso: string): string {
  return TIME.format(parseUtc(iso));
}

export function formatDateTime(iso: string): string {
  return DATE_TIME.format(parseUtc(iso));
}
