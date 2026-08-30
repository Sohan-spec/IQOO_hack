plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.relay.owner_app"
    compileSdk = flutter.compileSdkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "com.relay.owner_app"
        minSdk = maxOf(24, flutter.minSdkVersion)
        targetSdk = flutter.targetSdkVersion
        versionCode = 11
        versionName = "1.0.10"
        ndk {
            abiFilters.clear()
            abiFilters += listOf("arm64-v8a")
        }
        buildConfigField(
            "String",
            "RELAY_WS_URL",
            "\"${project.findProperty("RELAY_WS_URL") ?: "wss://sohan-spec--relay.modal.run/connect"}\"",
        )
        // RELAY_SECRET and CHECKOUT_CONFIRM_SECRET are not baked into the APK.
        // Paste them on the Settings screen; they are stored with Keystore-backed DataStore.
    }

    buildFeatures {
        buildConfig = true
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

chaquopy {
    defaultConfig {
        version = "3.13"
        buildPython("python3.13")
    }
    sourceSets {
        getByName("main") {
            srcDir("../../../backend")
        }
    }
}

flutter {
    source = "../.."
}

dependencies {
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("androidx.datastore:datastore-preferences:1.2.1")
}
