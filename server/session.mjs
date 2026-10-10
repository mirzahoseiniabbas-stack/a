const OPEN_DAYS = new Set(['Sat', 'Sun', 'Mon', 'Tue', 'Wed']);

export function tehranParts(now = new Date()) {
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Tehran',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  });
  const parts = Object.fromEntries(fmt.formatToParts(now).map((p) => [p.type, p.value]));
  return {
    weekday: parts.weekday,
    minutes: Number(parts.hour) * 60 + Number(parts.minute),
    clock: `${parts.hour}:${parts.minute}:${parts.second}`,
  };
}

export function marketSession(now = new Date()) {
  const { weekday, minutes, clock } = tehranParts(now);
  let label = 'بسته';
  let phase = 'closed';
  if (!OPEN_DAYS.has(weekday)) {
    label = 'تعطیل';
    phase = 'holiday';
  } else if (minutes >= 8 * 60 + 45 && minutes < 9 * 60) {
    label = 'پیش‌گشایش';
    phase = 'preopen';
  } else if (minutes >= 9 * 60 && minutes <= 12 * 60 + 30) {
    label = 'باز';
    phase = 'open';
  }
  return {
    open: phase === 'open',
    phase,
    label,
    clock,
    note: 'شنبه تا چهارشنبه، ۹ تا ۱۲:۳۰ به وقت تهران. تعطیلات رسمی جدا اعمال نشده است.',
  };
}
