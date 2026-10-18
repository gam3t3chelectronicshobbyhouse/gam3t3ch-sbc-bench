/* Offline, on-demand export of actual report data. No network or render loop. */
(() => {
  const save = document.getElementById('save-snapshot');
  const status = document.getElementById('snapshot-status');
  const finite = n => typeof n === 'number' && Number.isFinite(n);
  const number = (n, digits = 2) => finite(n) ? n.toLocaleString(undefined, {maximumFractionDigits: digits}) : 'Unavailable';
  const source = 'github.com/gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench';
  let previousUrl = null;
  save.onclick = async () => {
    save.disabled = true;
    status.textContent = 'Preparing image from this saved run…';
    try {
      const measurements = [];
      for (const category of ['cpu', 'memory']) {
        for (const [name, value] of Object.entries(data.results[category] ?? {})) {
          if (value && typeof value === 'object' && 'unit' in value) {
            measurements.push([category.toUpperCase() + ' / ' + name, number(value.value) + ' ' + value.unit, number(value.seconds, 3) + ' s']);
          }
        }
      }
      for (const scene of data.results.gpu?.scenes ?? []) measurements.push(['GLES2 / scene ' + scene.scene, number(scene.average_fps) + ' FPS · 1% low ' + number(scene.one_percent_low_fps), number(scene.seconds, 3) + ' s']);
      for (const scene of data.results.showcase?.scenes ?? []) measurements.push(['Godot / ' + scene.name, number(scene.average_fps) + ' FPS · 1% low ' + number(scene.one_percent_low_fps), number(scene.seconds, 3) + ' s']);
      for (const [index, drive] of (data.results.storage?.drives ?? []).entries()) {
        const driveName = ['Drive ' + (index + 1), drive.target.media, drive.target.model].filter(Boolean).join(' · ');
        for (const [name, value] of Object.entries(drive.tests ?? {})) {
          measurements.push([driveName + ' / ' + name, value.status === 'passed' ? number(value.mb_s) + ' MB/s · ' + number(value.iops, 1) + ' IOPS' : value.status,
            value.status === 'passed' ? 'Mean ' + number(value.latency_mean_ms, 3) + ' / p99 ' + number(value.latency_p99_ms, 3) + ' ms' : value.reason ?? 'Unavailable']);
        }
      }
      const statuses = Object.entries(data.test_status ?? {});
      const fields = [['temperature_c', 'Temperature', '°C', 1, '#62efd0'], ['cpu_mhz', 'CPU frequency', 'MHz', 1, '#b6a1ff'],
        ['cpu_utilization', 'CPU load', '%', 1, '#63b8ff'], ['memory_used_bytes', 'RAM in use', 'MiB', 1048576, '#ffca85'],
        ['swap_used_bytes', 'Swap in use', 'MiB', 1048576, '#ee97c8'], ['zram_used_bytes', 'Zram physical use', 'MiB', 1048576, '#a2dc71'],
        ['pressure_percent', 'Memory pressure · some avg10', '%', 1, '#ffc06d']];
      const height = 1160 + Math.ceil(fields.length / 2) * 245 + measurements.length * 72 + statuses.length * 64 + 310;
      if (height > 30000) throw Error('This report is too large for one PNG. Use Print / save PDF for the full report.');
      const canvas = document.createElement('canvas');
      canvas.width = 1600; canvas.height = height;
      const c = canvas.getContext('2d');
      c.fillStyle = '#0b1018'; c.fillRect(0, 0, canvas.width, canvas.height);
      function text(value, x, y, size = 24, color = '#eef4fc', weight = 400, max = 1480) {
        c.fillStyle = color; c.font = weight + ' ' + size + 'px system-ui, sans-serif';
        let line = String(value ?? 'Unavailable').replace(/[\r\n]+/g, ' ');
        while (line.length && c.measureText(line).width > max) line = line.slice(0, -2);
        c.fillText(line, x, y);
      }
      function panel(x, y, w, h) { c.fillStyle = '#131d2a'; c.fillRect(x, y, w, h); c.strokeStyle = '#27374b'; c.strokeRect(x, y, w, h); }
      text('G3', 54, 102, 58, '#ffad68', 800); text('GAM3T3CH 3D BENCHMARK', 175, 90, 42, '#62efd0', 800);
      text('PERFORMANCE LAB · SAVED-RUN SNAPSHOT', 175, 126, 19, '#98aac0', 600);
      text(data.hardware.board_model, 55, 210, 46, '#eef4fc', 750);
      text([data.hardware.cpu, data.hardware.architecture, finite(data.hardware.ram_bytes) ? number(data.hardware.ram_bytes / 1073741824, 2) + ' GiB RAM' : 'RAM unavailable'].filter(Boolean).join(' · '), 55, 255, 25);
      const osMatch = String(data.hardware.os ?? '').match(/PRETTY_NAME="?([^"\n]+)/);
      text('OS: ' + (osMatch?.[1] ?? data.hardware.os ?? 'Unavailable'), 55, 299, 22, '#98aac0');
      text('Suite ' + data.benchmark_version + ' · ' + data.workload_id + ' · ' + data.classification + ' / ' + data.status, 55, 345, 25, '#62efd0', 600);
      text('Run: ' + (data.run_id ?? 'not recorded') + ' · UTC: ' + (data.timestamp ?? 'not recorded'), 55, 385, 20, '#98aac0');
      text('Duration: ' + number(data.duration_seconds, 1) + ' s · Presentation: ' + (data.configuration.fullscreen ? 'fullscreen' : 'windowed / not applicable'), 55, 425, 22);
      const resolution = data.configuration.resolution;
      const storageConfig = data.results.storage?.configuration ?? data.configuration;
      text('Render: ' + (resolution?.join(' × ') ?? 'not applicable') + ' · Memory buffer: ' + number(data.configuration.memory_buffer_bytes / 1048576, 0) + ' MiB · Storage file: ' + number(storageConfig.size_mib, 0) + ' MiB', 55, 466, 21, '#98aac0');
      text('GPU: ' + (data.hardware.gpu_renderer ?? 'Unavailable') + ' · Engine/driver: ' + (data.results.showcase?.engine_version ?? data.hardware.graphics_driver ?? 'Unavailable'), 55, 507, 20, '#98aac0');
      const keys = ['cpu', 'memory', 'gpu', 'overall'];
      keys.forEach((key, index) => { const x = 55 + index * 380; panel(x, 545, 355, 125); text(key.toUpperCase(), x + 20, 579, 20, '#98aac0', 600, 310); text(finite(data.scores[key]) ? number(data.scores[key], 0) : 'Unavailable', x + 20, 630, 36, '#62efd0', 750, 315); });
      text('Provisional synthetic-reference points. Godot and storage raw results remain separate.', 55, 716, 21, '#ffca85');
      const thermal = data.thermal_summary ?? {};
      text('Temperature: start ' + number(thermal.start_c, 1) + ' · average ' + number(thermal.average_c, 1) + ' · peak ' + number(thermal.peak_c, 1) + ' · end ' + number(thermal.end_c, 1) + ' °C', 55, 760, 23);
      text('Throttling: ' + (typeof thermal.throttling_observed === 'boolean' ? thermal.throttling_observed ? 'observed' : 'not observed' : 'Unavailable') + ' · Background load accepted: ' + (data.configuration.background_load_accepted ? 'yes' : 'no / not recorded'), 55, 800, 22);
      const policies = data.hardware.tuning?.cpu_policies ?? [];
      text('Governor: ' + ([...new Set(policies.map(row => row.scaling_governor).filter(Boolean))].join(', ') || 'Unavailable') + ' · Stock/overclock status is not inferred from frequency.', 55, 840, 21, '#98aac0');
      if (document.getElementById('snapshot-notes').checked) text('Run notes: ' + [data.configuration.label, data.configuration.notes].filter(Boolean).join(' · '), 55, 884, 20, '#98aac0');
      else text('Hostname, IPs, mount paths and personal run notes are omitted from this image.', 55, 884, 20, '#98aac0');
      text('SYSTEM BEHAVIOUR THROUGHOUT THE RUN', 55, 950, 25, '#62efd0', 700);
      const end = Math.max(1, ...(data.telemetry ?? []).map(s => s.elapsed_seconds).filter(finite));
      fields.forEach(([field, label, unit, divisor, color], index) => {
        const x = 55 + (index % 2) * 760, y = 980 + Math.floor(index / 2) * 245;
        panel(x, y, 735, 220); text(label + ' · ' + unit, x + 18, y + 30, 21, '#98aac0', 600, 690);
        const samples = (data.telemetry ?? []).filter(s => finite(s[field]) && finite(s.elapsed_seconds));
        if (!samples.length) { text('Sensor unavailable', x + 28, y + 125, 24, '#98aac0'); return; }
        const maximum = Math.max(1, ...samples.map(s => s[field] / divisor));
        const left = x + 70, top = y + 55, width = 635, plotHeight = 120;
        c.strokeStyle = '#40536b'; c.beginPath(); c.moveTo(left, top); c.lineTo(left, top + plotHeight); c.lineTo(left + width, top + plotHeight); c.stroke();
        text(number(maximum, 1), x + 8, top + 12, 17, '#98aac0', 400, 58); text('0', x + 34, top + plotHeight + 4, 17, '#98aac0');
        text('0 s', left, top + plotHeight + 28, 17, '#98aac0'); text(number(end, 1) + ' s', left + width - 100, top + plotHeight + 28, 17, '#98aac0');
        c.strokeStyle = color; c.lineWidth = 2; c.beginPath();
        samples.forEach((sample, i) => { const px = left + width * sample.elapsed_seconds / end, py = top + plotHeight * (1 - sample[field] / divisor / maximum); if (!i) c.moveTo(px, py); else c.lineTo(px, py); }); c.stroke(); c.lineWidth = 1;
      });
      let y = 1020 + Math.ceil(fields.length / 2) * 245;
      text('RAW WORKLOAD MEASUREMENTS', 55, y, 25, '#62efd0', 700); y += 42;
      for (const [name, value, detail] of measurements) { panel(55, y - 25, 1490, 67); text(name, 70, y, 20, '#98aac0', 500, 700); text(value, 790, y, 22, '#eef4fc', 600, 730); text(detail, 790, y + 26, 18, '#98aac0', 400, 730); y += 72; }
      if (!measurements.length) { text('No completed workload measurements.', 55, y, 23, '#98aac0'); y += 60; }
      y += 40; text('TEST COMPLETION / AVAILABILITY', 55, y, 25, '#62efd0', 700); y += 40;
      for (const [name, test] of statuses) { text(name + ' · ' + test.status.toUpperCase(), 55, y, 21, test.status === 'passed' ? '#62efd0' : '#ffca85', 600); text(test.reason ?? '', 55, y + 27, 18, '#98aac0', 400, 1480); y += 64; }
      y += 30;
      text('REFERENCE: ' + source, 55, y, 18, '#98aac0');
      text('METHOD: ' + source + '/blob/main/docs/METHODOLOGY.md', 55, y + 30, 17, '#98aac0');
      text('Match suite, workload, engine/build and settings. Use repeated runs; a single result does not prove a tuning gain.', 55, y + 65, 19, '#ffca85');
      text('This is a performance checkup, not a hardware-health certification. Share result.json for complete reproducibility.', 55, y + 96, 19, '#98aac0');
      const blob = await new Promise((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(Error('PNG creation failed. Use Print / save PDF instead.')), 'image/png'));
      if (previousUrl) URL.revokeObjectURL(previousUrl);
      document.getElementById('snapshot-download')?.remove();
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      previousUrl = url;
      link.href = url; link.download = 'GAM3T3CH-' + String(data.hardware.board_model).replace(/[^a-z0-9_-]+/gi, '-').slice(0, 70) + '-stats.png';
      link.id = 'snapshot-download'; link.textContent = 'Download stats PNG';
      link.style.color = '#62efd0'; status.after(link);
      link.click();
      status.textContent = 'PNG ready. Use the download link if the automatic download did not start. Review it before posting; nothing was uploaded.';
    } catch (error) { status.textContent = error.message; }
    finally { save.disabled = false; }
  };
  document.getElementById('print-report').onclick = () => window.print();
})();
