import 'package:flutter/material.dart';

class RColors {
  static const purple = Color(0xFF6A24F4);
  static const purpleTint = Color(0xFFECE2FD);
  static const ink = Color(0xFF0D0D12);
  static const muted = Color(0xFF74747F);
  static const muted2 = Color(0xFF8A8A95);
  static const cardLine = Color(0xFFF1F1F4);
  static const bg = Color(0xFFFCFCFD);
  static const green = Color(0xFF3EA96A);
  static const greenBg = Color(0xFFE9F6EE);
  static const red = Color(0xFFE24747);
  static const redBg = Color(0xFFFDE8E8);
  static const search = Color(0xFFF1F1F4);
  static const cardBg = Color(0xFFFFFFFF);
  static const iconBtnBorder = Color(0xFFE9E9EE);
  static const switchOff = Color(0xFFDEDEE4);
  static const ghostBtnBg = Color(0xFFF2F2F5);
  static const ghostBtnText = Color(0xFF1C1C22);
  static const tabIdle = Color(0xFF83838E);
  static const tabBorder = Color(0xFFEDEDF1);
  static const chevron = Color(0xFFC4C4CC);
  static const placeholder = Color(0xFF9A9AA4);
  static const toastBg = Color(0xFF111119);
  static const toastText = Color(0xFFFFFFFF);
  static const toastCheck = Color(0xFF5EE08A);
  static const scrim = Color(0x6B0C0C14);
}

class RRadii {
  static const card = 16.0;
  static const iconBtn = 11.0;
  static const search = 12.0;
  static const chip = 10.0;
  static const menuIcon = 10.0;
  static const pill = 999.0;
  static const sheet = 26.0;
  static const button = 13.0;
  static const toast = 13.0;
}

class RShadow {
  static const card = [
    BoxShadow(
      color: Color(0x09121223),
      blurRadius: 3,
      offset: Offset(0, 1),
    ),
  ];
  static const sheet = [
    BoxShadow(
      color: Color(0x290C0C19),
      blurRadius: 40,
      offset: Offset(0, -12),
    ),
  ];
  static const knob = [
    BoxShadow(
      color: Color(0x33000000),
      blurRadius: 3,
      offset: Offset(0, 1),
    ),
  ];
}

class RSpace {
  static const screen = EdgeInsets.fromLTRB(20, 18, 20, 24);
}

class RText {
  static const _font = 'Manrope';

  static const pageTitle = TextStyle(
    fontFamily: _font,
    fontSize: 30,
    fontWeight: FontWeight.w800,
    color: RColors.ink,
    letterSpacing: -1.35,
    height: 1.0,
  );

  static const pageTitleSettings = TextStyle(
    fontFamily: _font,
    fontSize: 22,
    fontWeight: FontWeight.w800,
    color: RColors.ink,
    letterSpacing: -0.99,
    height: 1.0,
  );

  static const heroLabel = TextStyle(
    fontFamily: _font,
    fontSize: 15,
    fontWeight: FontWeight.w500,
    color: RColors.muted,
    letterSpacing: -0.18,
    height: 1.2,
  );

  static const heroAmount = TextStyle(
    fontFamily: _font,
    fontSize: 41,
    fontWeight: FontWeight.w800,
    color: RColors.ink,
    letterSpacing: -2.05,
    height: 1.05,
    fontFeatures: [FontFeature.tabularFigures()],
  );

  static const heroSub = TextStyle(
    fontFamily: _font,
    fontSize: 16,
    fontWeight: FontWeight.w500,
    color: RColors.muted,
    letterSpacing: -0.288,
    height: 1.2,
  );

  static const secH2 = TextStyle(
    fontFamily: _font,
    fontSize: 19,
    fontWeight: FontWeight.w800,
    color: RColors.ink,
    letterSpacing: -0.76,
    height: 1.2,
  );

  static const badge = TextStyle(
    fontFamily: _font,
    fontSize: 12.5,
    fontWeight: FontWeight.w700,
    color: Color(0xFFFFFFFF),
    letterSpacing: 0,
    height: 1.0,
  );

  static const link = TextStyle(
    fontFamily: _font,
    fontSize: 16,
    fontWeight: FontWeight.w700,
    color: RColors.purple,
    letterSpacing: -0.40,
  );

  static const profileLink = TextStyle(
    fontFamily: _font,
    fontSize: 15,
    fontWeight: FontWeight.w700,
    color: RColors.purple,
    letterSpacing: -0.40,
  );

  static const rowName = TextStyle(
    fontFamily: _font,
    fontSize: 17,
    fontWeight: FontWeight.w600,
    color: RColors.ink,
    letterSpacing: -0.476,
    height: 1.2,
  );

  static const rowTime = TextStyle(
    fontFamily: _font,
    fontSize: 14,
    fontWeight: FontWeight.w500,
    color: RColors.muted2,
    letterSpacing: -0.21,
    height: 1.2,
  );

  static const rowValue = TextStyle(
    fontFamily: _font,
    fontSize: 17,
    fontWeight: FontWeight.w600,
    color: RColors.ink,
    letterSpacing: -0.51,
    fontFeatures: [FontFeature.tabularFigures()],
  );

  static const payStatus = TextStyle(
    fontFamily: _font,
    fontSize: 13,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.26,
    height: 1.2,
  );

  static const empty = TextStyle(
    fontFamily: _font,
    fontSize: 15,
    fontWeight: FontWeight.w500,
    color: RColors.muted2,
    letterSpacing: -0.225,
  );

  static const searchInput = TextStyle(
    fontFamily: _font,
    fontSize: 15,
    fontWeight: FontWeight.w500,
    color: RColors.ink,
    letterSpacing: -0.30,
  );

  static const chip = TextStyle(
    fontFamily: _font,
    fontSize: 14,
    fontWeight: FontWeight.w600,
    color: RColors.muted2,
    letterSpacing: -0.28,
  );

  static const chipOn = TextStyle(
    fontFamily: _font,
    fontSize: 14,
    fontWeight: FontWeight.w600,
    color: RColors.purple,
    letterSpacing: -0.28,
  );

  static const dateLabel = TextStyle(
    fontFamily: _font,
    fontSize: 13,
    fontWeight: FontWeight.w600,
    color: RColors.muted2,
    letterSpacing: -0.13,
  );

  static const groupLabel = TextStyle(
    fontFamily: _font,
    fontSize: 12.5,
    fontWeight: FontWeight.w700,
    color: RColors.muted2,
    letterSpacing: 0.5625,
  );

  static const profileName = TextStyle(
    fontFamily: _font,
    fontSize: 18,
    fontWeight: FontWeight.w700,
    color: RColors.ink,
    letterSpacing: -0.54,
    height: 1.2,
  );

  static const profileEmail = TextStyle(
    fontFamily: _font,
    fontSize: 14,
    fontWeight: FontWeight.w500,
    color: RColors.muted2,
    letterSpacing: -0.21,
  );

  static const miTitle = TextStyle(
    fontFamily: _font,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    color: RColors.ink,
    letterSpacing: -0.448,
    height: 1.2,
  );

  static const miTitleDanger = TextStyle(
    fontFamily: _font,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    color: RColors.red,
    letterSpacing: -0.448,
    height: 1.2,
  );

  static const miSub = TextStyle(
    fontFamily: _font,
    fontSize: 13,
    fontWeight: FontWeight.w500,
    color: RColors.muted2,
    letterSpacing: -0.195,
    height: 1.25,
  );

  static const miSubOk = TextStyle(
    fontFamily: _font,
    fontSize: 13,
    fontWeight: FontWeight.w600,
    color: RColors.green,
    letterSpacing: -0.195,
    height: 1.25,
  );

  static const statusTitle = TextStyle(
    fontFamily: _font,
    fontSize: 16,
    fontWeight: FontWeight.w700,
    color: RColors.ink,
    letterSpacing: -0.48,
  );

  static const statusSub = TextStyle(
    fontFamily: _font,
    fontSize: 14,
    fontWeight: FontWeight.w500,
    color: Color(0xFF8A8A95),
    letterSpacing: -0.252,
  );

  static const tab = TextStyle(
    fontFamily: _font,
    fontSize: 13,
    fontWeight: FontWeight.w600,
    color: RColors.tabIdle,
    letterSpacing: -0.325,
  );

  static const tabOn = TextStyle(
    fontFamily: _font,
    fontSize: 13,
    fontWeight: FontWeight.w800,
    color: RColors.purple,
    letterSpacing: -0.325,
  );

  static const sheetTitle = TextStyle(
    fontFamily: _font,
    fontSize: 21,
    fontWeight: FontWeight.w800,
    color: RColors.ink,
    letterSpacing: -0.798,
  );

  static const sheetSub = TextStyle(
    fontFamily: _font,
    fontSize: 14,
    fontWeight: FontWeight.w500,
    color: RColors.muted2,
    letterSpacing: -0.21,
    height: 1.45,
  );

  static const sheetBig = TextStyle(
    fontFamily: _font,
    fontSize: 38,
    fontWeight: FontWeight.w800,
    color: RColors.ink,
    letterSpacing: -1.824,
    fontFeatures: [FontFeature.tabularFigures()],
  );

  static const kvKey = TextStyle(
    fontFamily: _font,
    fontSize: 15,
    fontWeight: FontWeight.w500,
    color: RColors.muted2,
    letterSpacing: -0.27,
  );

  static const kvValue = TextStyle(
    fontFamily: _font,
    fontSize: 15,
    fontWeight: FontWeight.w700,
    color: RColors.ink,
    letterSpacing: -0.27,
  );

  static const btn = TextStyle(
    fontFamily: _font,
    fontSize: 16,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.448,
  );

  static const toast = TextStyle(
    fontFamily: _font,
    fontSize: 15,
    fontWeight: FontWeight.w600,
    color: Color(0xFFFFFFFF),
    letterSpacing: -0.375,
  );

  static const avatarInitials = TextStyle(
    fontFamily: _font,
    fontSize: 12.5,
    fontWeight: FontWeight.w800,
    color: RColors.purple,
    letterSpacing: -0.125,
  );

  static const profileAvatar = TextStyle(
    fontFamily: _font,
    fontSize: 16,
    fontWeight: FontWeight.w800,
    color: RColors.purple,
    letterSpacing: -0.32,
  );
}
