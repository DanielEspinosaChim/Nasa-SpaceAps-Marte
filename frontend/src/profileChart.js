// Perfil altimétrico en <canvas>; los tramos de riesgo se sombrean.

const COLORS = { line: '#f2b66d', fill: '#f2b66d33', risk: '#f2c14e55', text: '#b89c8b', grid: '#4a2f22' };

export function profileBounds(profile) {
  const elev = profile.map((p) => p.elev_m);
  const lo = Math.min(...elev);
  const hi = Math.max(...elev);
  return { lo, hi: hi === lo ? lo + 1 : hi, total: profile[profile.length - 1].d_m || 1 };
}

export function drawProfile(canvas, profile) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || 300;
  const h = canvas.clientHeight || 120;
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  const ctx = canvas.getContext('2d');
  if (!ctx || !profile || profile.length < 2) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  const pad = { l: 44, r: 8, t: 8, b: 18 };
  const { lo, hi, total } = profileBounds(profile);
  const x = (d) => pad.l + (d / total) * (w - pad.l - pad.r);
  const y = (e) => pad.t + (1 - (e - lo) / (hi - lo)) * (h - pad.t - pad.b);

  // Tramos de riesgo.
  ctx.fillStyle = COLORS.risk;
  for (let i = 0; i < profile.length - 1; i++) {
    if (profile[i].risk || profile[i + 1].risk) {
      ctx.fillRect(x(profile[i].d_m), pad.t, Math.max(1, x(profile[i + 1].d_m) - x(profile[i].d_m)), h - pad.t - pad.b);
    }
  }
  // Área y línea.
  ctx.beginPath();
  ctx.moveTo(x(profile[0].d_m), h - pad.b);
  profile.forEach((p) => ctx.lineTo(x(p.d_m), y(p.elev_m)));
  ctx.lineTo(x(profile[profile.length - 1].d_m), h - pad.b);
  ctx.closePath();
  ctx.fillStyle = COLORS.fill;
  ctx.fill();
  ctx.beginPath();
  profile.forEach((p, i) => (i ? ctx.lineTo(x(p.d_m), y(p.elev_m)) : ctx.moveTo(x(p.d_m), y(p.elev_m))));
  ctx.strokeStyle = COLORS.line;
  ctx.lineWidth = 2;
  ctx.stroke();
  // Ejes.
  ctx.fillStyle = COLORS.text;
  ctx.font = '10px sans-serif';
  ctx.textAlign = 'right';
  ctx.fillText(`${hi.toFixed(0)} m`, pad.l - 4, pad.t + 8);
  ctx.fillText(`${lo.toFixed(0)} m`, pad.l - 4, h - pad.b);
  ctx.textAlign = 'right';
  ctx.fillText(`${(total / 1000).toFixed(1)} km`, w - pad.r, h - 4);
  ctx.textAlign = 'left';
  ctx.fillText('0', pad.l, h - 4);
}
