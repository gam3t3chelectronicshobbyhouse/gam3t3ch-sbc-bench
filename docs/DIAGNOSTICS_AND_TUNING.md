# Gaia Pi 5 findings and stock-setting checks

The supplied 0.4.0 image shows Debian 13/aarch64, a Pi 5, V3D graphics,
CPU/memory success and completed Godot scenes around 19–21 FPS. Its baseline
GLES program did not link, and the USB HDD random write failed after sequential
transfers succeeded. The image does not contain the full linker or fio error.
These are not evidence that the board or drive is defective.

The GLES sources used high-precision defaults in the vertex shader and medium
precision in the fragment shader for shared declarations. 0.5.0 explicitly
matches the shader precision and includes the driver program-link log. A real
Mesa software-context shader probe is included in CI; Gaia's V3D needs a rerun.

The old 1 GiB random 4 KiB test required 262,144 operations within 600 seconds.
A disk below roughly 437 IOPS could not meet that limit before extra flush costs.
The image's total duration is consistent with such a timeout, but only the
original result.json/engine.log can confirm the exact cause. New random stages
run for 20 seconds instead of requiring a whole-file byte count. Read tests can
continue after a random-write error if initial population succeeded. Workload
identity changed; do not compare old/new random-rate deltas as identical tests.

## Checks before clocks

Use the on-demand diagnostic button or `g3bench diagnostics`. Record the OS,
kernel, desktop/session, driver/API, engine and profile, not just the board name.
A successful vulkaninfo probe establishes availability, not that a GLES workload
is using Vulkan. Godot Compatibility uses OpenGL. The explicit Vulkan test
records its actual rendering driver and rejects a silent fallback.

If llvmpipe/softpipe/lavapipe is recorded, inspect forced software overrides and
the OS-supported Mesa/KMS stack. Test from the local desktop: no DISPLAY in an
SSH shell is not proof of broken hardware. A Wayland-only session can legitimately
lack a GLX probe. Keep X11/Wayland and renderer settings recorded when comparing.
Update through the distribution's supported packages; do not copy obsolete
config.txt recipes onto another board/OS. Check power/cooling warnings first.

Close capture/playback and other active tasks for baseline runs. Compare at least
three repeats with the same cooling, PSU, initial temperature, workload and
settings. Governor ramp-up affects brief tests: a documented performance-policy
experiment may be useful within stock frequency limits, but GAM3T3CH never
changes it automatically. Restore the original policy afterward. A cooler or
faster single run is not by itself proof of a tuning improvement.

For external drives, use lsusb -t to inspect the actual USB link and driver.
A 480M link may explain a USB 3 drive limit; check the relevant port/cable/enclosure.
A healthy HDD is naturally much slower than NVMe for random I/O. Inspect timeout,
I/O and power errors individually. Direct and buffered measurements are separate
experiments; the application does not hide a direct-I/O error with a fallback.

## GAM3T3CH references and other benchmark practices

- [gam3t3ch on element14](https://community.element14.com/members/gam3t3ch)
- [ALSA no-audio/glitch Pi 4 fix](https://community.element14.com/products/raspberry-pi/b/blog/posts/alsa-no-audio-glitch-issue-pi-4-fix)
- [Webcam freezing/lagging/jittering fix](https://community.element14.com/products/raspberry-pi/b/blog/posts/fix-raspberry-pi-webcam-freezing-lagging-jittering-issue)

These are historical Pi 4 troubleshooting references. The webcam article writes
a PCI register during startup; it is not a generic benchmark speed tweak and is
not applied by this program. Neither article establishes a current Pi 5 driver
fix. Verify the exact hardware, OS and symptom before reusing an older remedy.

The suite follows established practices of keeping workload definitions, raw
results, configuration and repeat statistics inspectable rather than assigning a
board-specific multiplier. Raw rates compare different boards doing the same
work. A legacy-resolution GPU test has its own group. No calibrated Pi-specific
reference database has been collected, so there is no fabricated star rating.

Primary technical references:

- [Raspberry Pi configuration / KMS](https://www.raspberrypi.com/documentation/computers/config_txt.html)
- [Khronos OpenGL ES specifications](https://registry.khronos.org/OpenGL/index_es.php)
- [Godot rendering methods](https://docs.godotengine.org/en/stable/tutorials/rendering/renderers.html)
- [fio time-based workloads](https://fio.readthedocs.io/en/latest/fio_doc.html)
- [iperf3 invocation and reverse mode](https://software.es.net/iperf/invoking.html)
- [Cloudflare speed-test component](https://github.com/cloudflare/speedtest)
- [Phoronix Test Suite documentation](https://github.com/phoronix-test-suite/phoronix-test-suite/blob/master/documentation/phoronix-test-suite.md)

Network, sustained SHA256 and Godot rates remain unscored. HTTP trials are small,
single-request end-to-end samples and may underestimate link capacity; they do
not measure ICMP latency, loaded latency or packet loss. iperf3 isolates a chosen
LAN path but still depends on the peer. The CPU load phase is not a memory,
storage endurance, video decode, audio latency or complete stability test.
