"""On-demand graphics environment checks and evidence-based, read-only advice."""
import glob
import os
import platform
import shutil
import subprocess
from .system import read, hardware

PI_DOCS = 'https://www.raspberrypi.com/documentation/computers/config_txt.html'
FIO_DOCS = 'https://fio.readthedocs.io/en/latest/fio_doc.html'

def probe(argv):
    path = shutil.which(argv[0])
    if not path:
        return {'status': 'unavailable', 'reason': argv[0] + ' is not installed; this does not prove the API is unsupported.'}
    try:
        p = subprocess.run([path, *argv[1:]], capture_output=True, text=True, timeout=12)
        return {'status': 'passed' if p.returncode == 0 else 'failed', 'exit_code': p.returncode,
                'output': (p.stdout + '\n' + p.stderr).strip()[:24000]}
    except (OSError, subprocess.SubprocessError) as exc:
        return {'status': 'failed', 'reason': str(exc)}

def test_profile(hw, requested='auto'):
    legacy = hw.get('board_profile', {}).get('model_id') in {'pi-1', 'zero', 'cm1'} or hw.get('architecture','').startswith('armv6')
    selected = ('legacy' if legacy else 'standard') if requested == 'auto' else requested
    return {'name': selected, 'selection': requested, 'gpu_resolution': [640,360] if selected == 'legacy' else [1280,720],
            'godot_recommended': not legacy, 'common_tests': ['cpu','memory','gles2'],
            'notes': 'CPU/memory work remains identical across boards. Legacy GPU results have a separate resolution group. No board-specific score multiplier.'}

def collect(probes=True):
    return {'session': {key: os.environ.get(key) for key in ('XDG_SESSION_TYPE','DISPLAY','WAYLAND_DISPLAY','SDL_VIDEODRIVER','LIBGL_ALWAYS_SOFTWARE','MESA_LOADER_DRIVER_OVERRIDE')},
            'kernel_modules': '\n'.join(line for line in (read('/proc/modules') or '').splitlines() if line.startswith(('v3d ', 'vc4 ', 'drm '))),
            'drm_nodes': glob.glob('/dev/dri/*'),
            'opengl': probe(['glxinfo','-B']) if probes and os.environ.get('DISPLAY') else {'status':'unavailable','reason':'No X11/XWayland display; this is normal in a Wayland-only session.'},
            'vulkan': probe(['vulkaninfo','--summary']) if probes else {'status':'unavailable','reason':'Use diagnostics for an explicit API probe'},
            'usb_topology': probe(['lsusb','-t']) if probes and platform.system() == 'Linux' else {'status':'unavailable'}}

def advice(data):
    findings=[]
    def add(level,title,detail,link=PI_DOCS): findings.append({'level':level,'title':title,'detail':detail,'reference':link})
    diag=data.get('diagnostics',{})
    text=str(diag).lower()+' '+str(data.get('hardware',{}).get('gpu_renderer','')).lower()+' '+str(data.get('results',{}).get('showcase',{}).get('renderer','')).lower()
    if any(word in text for word in ('llvmpipe','softpipe','lavapipe','swiftshader')):
        add('warning','Software graphics detected','A software renderer can limit FPS. Check the OS-supported Mesa/KMS driver stack and local desktop session; remove forced software overrides only after checking why they were set.')
    if diag.get('vulkan',{}).get('status') != 'passed':
        add('info','Vulkan not verified','Install vulkan-tools through your distribution and run vulkaninfo --summary. A missing probe is not evidence that Vulkan is broken. GLES2 and Godot Compatibility do not use Vulkan.','https://docs.godotengine.org/en/stable/tutorials/rendering/renderers.html')
    if diag and not diag.get('session',{}).get('DISPLAY') and not diag.get('session',{}).get('WAYLAND_DISPLAY') and data.get('hardware',{}).get('platform')=='Linux':
        add('warning','No desktop display in this launch environment','Launch graphics tests from the local desktop. An SSH session without display access cannot measure on-screen rendering.')
    if data.get('configuration',{}).get('background_load_accepted'):
        add('info','Background load accepted','Close browsers playing media, video capture, package updates and other heavy tasks, then repeat three times with idle checking enabled.')
    bits=[s.get('throttled_bits') for s in data.get('telemetry',[]) if isinstance(s.get('throttled_bits'),int)]
    if any(b & 1 for b in bits): add('warning','Undervoltage observed','Check the rated power supply, USB-C cable and peripheral power budget before tuning clocks.')
    if any(b & 4 for b in bits): add('warning','Active throttling observed','Inspect heatsink contact, fan operation and airflow, and rerun from a similar starting temperature.')
    policies=data.get('hardware',{}).get('tuning',{}).get('cpu_policies',[])
    if any(p.get('scaling_governor') in ('ondemand','powersave') for p in policies):
        add('info','Frequency policy recorded','Governor ramp-up can affect short CPU tests. Compare a documented performance-governor run only within stock frequency limits; do not change it silently, and restore the original policy afterward.')
    for drive in data.get('results',{}).get('storage',{}).get('drives',[]):
        if drive.get('status')!='passed': add('warning','Drive workload incomplete',str(drive.get('reason'))+' Inspect per-stage error and USB link/power; a timeout is not a failed-drive diagnosis.',FIO_DOCS)
    if '480M' in str(diag.get('usb_topology','')): add('info','USB 2 link present','Check which device uses the 480M link. For a USB 3 drive, verify its port, cable and enclosure; other USB 2 devices may be entirely normal.')
    add('info','Compare stock configurations','Keep OS, compiler, renderer/API, resolution, cooling and starting temperature documented. Use repeated runs and raw metrics across Pi 4, Pi 5 and CM5; no fabricated per-board reference ratings.')
    return findings
