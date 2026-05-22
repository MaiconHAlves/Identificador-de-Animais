package org.kivy.android;

import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CaptureRequest;
import android.media.Image;
import android.media.ImageReader;
import android.graphics.ImageFormat;
import android.os.Handler;
import android.os.HandlerThread;
import android.content.Context;
import android.util.Range;
import android.util.Log;
import java.util.Arrays;
import java.nio.ByteBuffer;

/**
 * Wrapper Java para Camera2 API.
 * Necessário porque CameraDevice.StateCallback e CameraCaptureSession.StateCallback
 * são classes abstratas — pyjnius só pode implementar interfaces Java, não classes abstratas.
 * Esta classe encapsula as abstratas e expõe FrameCallback (interface) para Python.
 */
public class CameraHelper {

    public interface FrameCallback {
        void onFrame(byte[] y, byte[] u, byte[] v, int width, int height, int yPixelStride, int yRowStride, int uPixelStride, int uRowStride, int vPixelStride, int vRowStride);
        void onError(String message);
        void onOpened();
    }

    private CameraDevice       mCamera;
    private CameraCaptureSession mSession;
    private ImageReader        mImageReader;
    private HandlerThread      mThread;
    private Handler            mHandler;

    public void open(Context ctx, String cameraId, int width, int height,
                     final FrameCallback cb) {

        mThread = new HandlerThread("CameraHelper");
        mThread.start();
        mHandler = new Handler(mThread.getLooper());
        Log.d("CameraHelper", "Iniciando abertura da câmera: " + cameraId);

        mImageReader = ImageReader.newInstance(width, height, ImageFormat.YUV_420_888, 2);
        mImageReader.setOnImageAvailableListener(reader -> {
            Image img = reader.acquireLatestImage();
            if (img == null) return;
            try {
                Image.Plane[] planes = img.getPlanes();
                
                // Conversão de alta performance para Python (evita erro de ByteBuffer)
                ByteBuffer yBuf = planes[0].getBuffer();
                ByteBuffer uBuf = planes[1].getBuffer();
                ByteBuffer vBuf = planes[2].getBuffer();

                byte[] yArr = new byte[yBuf.remaining()];
                byte[] uArr = new byte[uBuf.remaining()];
                byte[] vArr = new byte[vBuf.remaining()];

                yBuf.get(yArr);
                uBuf.get(uArr);
                vBuf.get(vArr);

                cb.onFrame(
                    yArr, uArr, vArr,
                    img.getWidth(), 
                    img.getHeight(),
                    planes[0].getPixelStride(),
                    planes[0].getRowStride(),
                    planes[1].getPixelStride(),
                    planes[1].getRowStride(),
                    planes[2].getPixelStride(),
                    planes[2].getRowStride()
                );
            } catch (Exception e) {
                cb.onError("frame error: " + e.getMessage());
            } finally {
                img.close();
            }
        }, mHandler);

        CameraManager mgr = (CameraManager) ctx.getSystemService(Context.CAMERA_SERVICE);
        try {
            mgr.openCamera(cameraId, new CameraDevice.StateCallback() {
                @Override
                public void onOpened(CameraDevice cam) {
                    Log.d("CameraHelper", "Câmera aberta com sucesso: " + cameraId);
                    mCamera = cam;
                    try {
                        cam.createCaptureSession(
                            Arrays.asList(mImageReader.getSurface()),
                            new CameraCaptureSession.StateCallback() {
                                @Override
                                public void onConfigured(CameraCaptureSession sess) {
                                    mSession = sess;
                                    try {
                                        CaptureRequest.Builder req = cam.createCaptureRequest(
                                            CameraDevice.TEMPLATE_PREVIEW);
                                        req.addTarget(mImageReader.getSurface());
                                        req.set(CaptureRequest.CONTROL_AE_TARGET_FPS_RANGE, new Range<>(15, 30));
                                        req.set(CaptureRequest.CONTROL_AF_MODE,
                                            CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
                                        sess.setRepeatingRequest(req.build(),
                                            new CameraCaptureSession.CaptureCallback() {
                                                @Override
                                                public void onCaptureFailed(CameraCaptureSession s,
                                                        CaptureRequest r,
                                                        android.hardware.camera2.CaptureFailure f) {
                                                    cb.onError("capture failed: " + f.getReason());
                                                }
                                            }, mHandler);
                                        cb.onOpened();
                                    } catch (Exception e) {
                                        cb.onError("capture error: " + e.getMessage());
                                    }
                                }
                                @Override
                                public void onConfigureFailed(CameraCaptureSession sess) {
                                    cb.onError("session config failed");
                                }
                            }, mHandler);
                    } catch (Exception e) {
                        cb.onError("createCaptureSession: " + e.getMessage());
                    }
                }
                @Override
                public void onDisconnected(CameraDevice cam) {
                    Log.w("CameraHelper", "Câmera desconectada: " + cameraId);
                    cam.close();
                    cb.onError("camera disconnected");
                }
                @Override
                public void onError(CameraDevice cam, int err) {
                    Log.e("CameraHelper", "Erro na câmera " + cameraId + ": código " + err);
                    cam.close();
                    cb.onError("camera error code: " + err);
                }
            }, mHandler);
        } catch (Exception e) {
            cb.onError("openCamera: " + e.getMessage());
        }
    }

    public void close() {
        try { if (mSession    != null) mSession.close();    } catch (Exception ignored) {}
        try { if (mCamera     != null) mCamera.close();     } catch (Exception ignored) {}
        try { if (mImageReader != null) mImageReader.close();} catch (Exception ignored) {}
        try { if (mThread     != null) mThread.quit();      } catch (Exception ignored) {}
        mSession = null; mCamera = null; mImageReader = null; mThread = null;
    }
}
