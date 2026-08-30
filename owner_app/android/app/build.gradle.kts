import java.util.Properties

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
        versionCode = 16
        versionName = "1.0.15-demo"
        ndk {
            abiFilters.clear()
            abiFilters += listOf("arm64-v8a")
        }
        buildConfigField(
            "String",
            "RELAY_WS_URL",
            "\"${project.findProperty("RELAY_WS_URL") ?: "wss://sohan-spec--relay.modal.run/connect"}\"",
        )
        // RELAY_SECRET and CHECKOUT_CONFIRM_SECRET are never baked into release
        // APKs. Debug APKs may seed an empty Keystore store from
        // android/debug-secrets.properties (gitignored).
    }

    buildFeatures {
        buildConfig = true
    }

    buildTypes {
        debug {
            val secretsFile = rootProject.file("debug-secrets.properties")
            val secrets = Properties()
            if (secretsFile.exists()) {
                secretsFile.inputStream().use { secrets.load(it) }
            }
            fun debugSecret(key: String): String {
                val raw = secrets.getProperty(key, "")?.trim().orEmpty()
                return raw.replace("\\", "\\\\").replace("\"", "\\\"")
            }
            buildConfigField("String", "DEBUG_RELAY_SECRET", "\"${debugSecret("RELAY_SECRET")}\"")
            buildConfigField("String", "DEBUG_CONFIRM_SECRET", "\"${debugSecret("CHECKOUT_CONFIRM_SECRET")}\"")
        }
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
