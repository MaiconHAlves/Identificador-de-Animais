plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "br.com.litert_poc"
    compileSdk = 36

    defaultConfig {
        applicationId = "br.com.litert_poc"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }

    kotlinOptions {
        jvmTarget = "11"
    }

    // Evita conflito de .so duplicados entre LiteRT + AICore
    packaging {
        jniLibs {
            pickFirsts += listOf("lib/**/libtensorflowlite_jni.so")
        }
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)

    // LiteRT runtime (substitui tflite-support + tflite-task-*)
    implementation(libs.litert)
    // AICore delegate — aceleração NPU/GPU via Android AICore (Exynos 2400, Tensor G4, etc.)
    implementation(libs.litert.aicore)
}
