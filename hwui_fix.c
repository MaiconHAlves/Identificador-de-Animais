/*
 * hwui_fix.c — Samsung Android 16 HWUI CommonPool crash workaround
 *
 * Root cause: Samsung's libhwui.so creates and immediately destroys
 * RenderThread::CommonPool (probe-and-destroy pattern) when hardwareAccelerated=false
 * is detected. Worker threads (hwuiTask0/1) start before the destructor runs,
 * then try to lock the already-destroyed mutex → FORTIFY SIGABRT.
 *
 * Fix: intercept SIGABRT. If the crashing thread is named "hwuiTask*",
 * exit only that thread (pthread_exit) instead of aborting the whole process.
 * SDL2/Kivy renders via EGL/OpenGL ES directly and does not need HWUI.
 */
#include <signal.h>
#include <pthread.h>
#include <sys/prctl.h>
#include <string.h>
#include <stdlib.h>
#include <android/log.h>

#define LOG_TAG "HwuiFix"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO,  LOG_TAG, __VA_ARGS__)
#define LOGW(...) __android_log_print(ANDROID_LOG_WARN,  LOG_TAG, __VA_ARGS__)

static struct sigaction g_original_sigabrt;

static void hwui_sigabrt_handler(int sig, siginfo_t *info, void *ucontext) {
    char name[16] = {0};
    prctl(PR_GET_NAME, name, 0, 0, 0);

    if (strncmp(name, "hwuiTask", 8) == 0) {
        /* Samsung HWUI CommonPool race — silently exit this worker thread.
         * The process (Python/Kivy/SDL2) is unaffected. */
        LOGW("hwui_fix: caught SIGABRT on %s — exiting thread (Samsung HWUI bug workaround)", name);
        pthread_exit(NULL);
        /* pthread_exit never returns */
    }

    /* Not a hwuiTask thread — restore original handler and re-raise normally */
    LOGW("hwui_fix: SIGABRT on thread '%s' — forwarding to original handler", name);
    sigaction(SIGABRT, &g_original_sigabrt, NULL);
    raise(SIGABRT);
}

/* Called automatically when System.loadLibrary("hwuifix") executes */
__attribute__((constructor))
static void install_hwui_fix(void) {
    struct sigaction sa;
    sigemptyset(&sa.sa_mask);
    sa.sa_sigaction = hwui_sigabrt_handler;
    sa.sa_flags = SA_SIGINFO | SA_RESTART;
    if (sigaction(SIGABRT, &sa, &g_original_sigabrt) == 0) {
        LOGI("hwui_fix: SIGABRT handler installed (Samsung Android 16 HWUI workaround)");
    }
}
