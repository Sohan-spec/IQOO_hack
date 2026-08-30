import 'package:flutter/services.dart';

const _channel = MethodChannel('com.relay.owner/device');

class DeviceBridge {
  Future<bool> notificationAccessGranted() async {
    final value = await _channel.invokeMethod<bool>('notificationAccessGranted');
    return value ?? false;
  }

  Future<void> openNotificationAccessSettings() {
    return _channel.invokeMethod<void>('openNotificationAccessSettings');
  }

  Future<int> interruptionFilter() async {
    final value = await _channel.invokeMethod<int>('getInterruptionFilter');
    return value ?? 0;
  }

  Future<void> requestPostNotifications() {
    return _channel.invokeMethod<void>('requestPostNotifications');
  }

  Future<bool> batteryOptimizationIgnored() async {
    final value = await _channel.invokeMethod<bool>('batteryOptimizationIgnored');
    return value ?? false;
  }

  Future<void> requestIgnoreBatteryOptimizations() {
    return _channel.invokeMethod<void>('requestIgnoreBatteryOptimizations');
  }

  Future<void> runSetupPrompts() {
    return _channel.invokeMethod<void>('runSetupPrompts');
  }

  Future<String> getDefaultCallbackUrl() async {
    final value = await _channel.invokeMethod<String>('getDefaultCallbackUrl');
    return value ?? '';
  }

  Future<void> setDefaultCallbackUrl(String url) {
    return _channel.invokeMethod<void>(
      'setDefaultCallbackUrl',
      <String, dynamic>{'url': url},
    );
  }

  Future<bool> relayConnected() async {
    final value = await _channel.invokeMethod<bool>('relayConnected');
    return value ?? false;
  }

  Future<String> relayMerchantId() async {
    final value = await _channel.invokeMethod<String>('relayMerchantId');
    return value ?? '';
  }

  Future<bool> relaySecretConfigured() async {
    final value = await _channel.invokeMethod<bool>('relaySecretConfigured');
    return value ?? false;
  }

  Future<String> relaySecret() async {
    final value = await _channel.invokeMethod<String>('relaySecret');
    return value ?? '';
  }

  Future<void> setRelaySecret(String secret) {
    return _channel.invokeMethod<void>(
      'setRelaySecret',
      <String, dynamic>{'secret': secret},
    );
  }

  Future<bool> checkoutConfirmSecretConfigured() async {
    final value = await _channel.invokeMethod<bool>(
      'checkoutConfirmSecretConfigured',
    );
    return value ?? false;
  }

  Future<String> checkoutConfirmSecret() async {
    final value = await _channel.invokeMethod<String>('checkoutConfirmSecret');
    return value ?? '';
  }

  Future<void> setCheckoutConfirmSecret(String secret) {
    return _channel.invokeMethod<void>(
      'setCheckoutConfirmSecret',
      <String, dynamic>{'secret': secret},
    );
  }
}

/// android.app.NotificationManager interruption filter constants.
class InterruptionFilter {
  static const unknown = 0;
  static const all = 1;
  static const priority = 2;
  static const none = 3;
  static const alarms = 4;

  static String label(int value) {
    switch (value) {
      case all:
        return 'All (DND off)';
      case priority:
        return 'Priority only';
      case none:
        return 'Total silence';
      case alarms:
        return 'Alarms only';
      default:
        return 'Unknown';
    }
  }

  static bool isDndOn(int value) => value != all;
}
