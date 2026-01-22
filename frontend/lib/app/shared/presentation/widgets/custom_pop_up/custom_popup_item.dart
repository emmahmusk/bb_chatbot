import 'package:flutter/material.dart';

class CustomPopUpItem<T> extends PopupMenuEntry<T> {
  /// Creates an item for a popup menu.
  ///
  /// By default, the item is [enabled].
  const CustomPopUpItem({
    super.key,
    this.value,
    this.onTap,
    this.enabled = true,
    this.height = kMinInteractiveDimension,
    this.padding,
    this.textStyle,
    this.labelTextStyle,
    this.mouseCursor,
    required this.child,
  });

  /// The value that will be returned by [showMenu] if this entry is selected.
  final T? value;

  /// Called when the menu item is tapped.
  final VoidCallback? onTap;

  /// Whether the user is permitted to select this item.
  ///
  /// Defaults to true. If this is false, then the item will not react to
  /// touches.
  final bool enabled;

  /// The minimum height of the menu item.
  ///
  /// Defaults to [kMinInteractiveDimension] pixels.
  @override
  final double height;

  /// The padding of the menu item.
  ///
  /// The [height] property may interact with the applied padding. For example,
  /// If a [height] greater than the height of the sum of the padding and [child]
  /// is provided, then the padding's effect will not be visible.
  ///
  /// If this is null and [ThemeData.useMaterial3] is true, the horizontal padding
  /// defaults to 12.0 on both sides.
  ///
  /// If this is null and [ThemeData.useMaterial3] is false, the horizontal padding
  /// defaults to 16.0 on both sides.
  final EdgeInsets? padding;

  /// The text style of the popup menu item.
  ///
  /// If this property is null, then [PopupMenuThemeData.textStyle] is used.
  /// If [PopupMenuThemeData.textStyle] is also null, then [TextTheme.titleMedium]
  /// of [ThemeData.textTheme] is used.
  final TextStyle? textStyle;

  /// The label style of the popup menu item.
  ///
  /// When [ThemeData.useMaterial3] is true, this styles the text of the popup menu item.
  ///
  /// If this property is null, then [PopupMenuThemeData.labelTextStyle] is used.
  /// If [PopupMenuThemeData.labelTextStyle] is also null, then [TextTheme.labelLarge]
  /// is used with the [ColorScheme.onSurface] color when popup menu item is enabled and
  /// the [ColorScheme.onSurface] color with 0.38 opacity when the popup menu item is disabled.
  final WidgetStateProperty<TextStyle?>? labelTextStyle;

  /// {@template flutter.material.popupmenu.mouseCursor}
  /// The cursor for a mouse pointer when it enters or is hovering over the
  /// widget.
  ///
  /// If [mouseCursor] is a [MaterialStateProperty<MouseCursor>],
  /// [WidgetStateProperty.resolve] is used for the following [WidgetState]s:
  ///
  ///  * [WidgetState.hovered].
  ///  * [WidgetState.focused].
  ///  * [WidgetState.disabled].
  /// {@endtemplate}
  ///
  /// If null, then the value of [PopupMenuThemeData.mouseCursor] is used. If
  /// that is also null, then [WidgetStateMouseCursor.clickable] is used.
  final MouseCursor? mouseCursor;

  /// The widget below this widget in the tree.
  ///
  /// Typically a single-line [ListTile] (for menus with icons) or a [Text]. An
  /// appropriate [DefaultTextStyle] is put in scope for the child. In either
  /// case, the text should be short enough that it won't wrap.
  final Widget? child;

  @override
  bool represents(T? value) => value == this.value;

  @override
  PopupMenuItemState<T, CustomPopUpItem<T>> createState() =>
      PopupMenuItemState<T, CustomPopUpItem<T>>();
}

/// The [State] for [CustomPopUpItem] subclasses.
///
/// By default this implements the basic styling and layout of Material Design
/// popup menu items.
///
/// The [buildChild] method can be overridden to adjust exactly what gets placed
/// in the menu. By default it returns [CustomPopUpItem.child].
///
/// The [handleTap] method can be overridden to adjust exactly what happens when
/// the item is tapped. By default, it uses [Navigator.pop] to return the
/// [CustomPopUpItem.value] from the menu route.
///
/// This class takes two type arguments. The second, `W`, is the exact type of
/// the [Widget] that is using this [State]. It must be a subclass of
/// [CustomPopUpItem]. The first, `T`, must match the type argument of that widget
/// class, and is the type of values returned from this menu.
class PopupMenuItemState<T, W extends CustomPopUpItem<T>> extends State<W> {
  /// The menu item contents.
  ///
  /// Used by the [build] method.
  ///
  /// By default, this returns [CustomPopUpItem.child]. Override this to put
  /// something else in the menu entry.
  @protected
  Widget? buildChild() => widget.child;

  /// The handler for when the user selects the menu item.
  ///
  /// Used by the [InkWell] inserted by the [build] method.
  ///
  /// By default, uses [Navigator.pop] to return the [CustomPopUpItem.value] from
  /// the menu route.
  @protected
  void handleTap() {
    // Need to pop the navigator first in case onTap may push new route onto navigator.
    Navigator.pop<T>(context, widget.value);

    widget.onTap?.call();
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final PopupMenuThemeData popupMenuTheme = PopupMenuTheme.of(context);
    final PopupMenuThemeData defaults = theme.useMaterial3
        ? _PopupMenuDefaultsM3(context)
        : _PopupMenuDefaultsM2(context);
    final Set<WidgetState> states = <WidgetState>{
      if (!widget.enabled) WidgetState.disabled,
    };

    TextStyle style = theme.useMaterial3
        ? (widget.labelTextStyle?.resolve(states) ??
            popupMenuTheme.labelTextStyle?.resolve(states)! ??
            defaults.labelTextStyle!.resolve(states)!)
        : (widget.textStyle ?? popupMenuTheme.textStyle ?? defaults.textStyle!);

    if (!widget.enabled && !theme.useMaterial3) {
      style = style.copyWith(color: theme.disabledColor);
    }

    Widget item = AnimatedDefaultTextStyle(
      style: style,
      duration: kThemeChangeDuration,
      child: Container(
        alignment: AlignmentDirectional.centerStart,
        constraints: BoxConstraints(minHeight: widget.height),
        padding: widget.padding ??
            (theme.useMaterial3
                ? _PopupMenuDefaultsM3.menuHorizontalPadding
                : _PopupMenuDefaultsM2.menuHorizontalPadding),
        child: buildChild(),
      ),
    );

    if (!widget.enabled) {
      final bool isDark = theme.brightness == Brightness.dark;
      item = IconTheme.merge(
        data: IconThemeData(opacity: isDark ? 0.5 : 0.38),
        child: item,
      );
    }

    return MergeSemantics(
      child: Semantics(
        enabled: widget.enabled,
        button: false,
        child: item,
      ),
    );
  }
}

class _PopupMenuDefaultsM2 extends PopupMenuThemeData {
  _PopupMenuDefaultsM2(this.context) : super(elevation: 8.0);

  final BuildContext context;
  late final ThemeData _theme = Theme.of(context);
  late final TextTheme _textTheme = _theme.textTheme;

  @override
  TextStyle? get textStyle => _textTheme.titleMedium;

  static EdgeInsets menuHorizontalPadding =
      const EdgeInsets.symmetric(horizontal: 16.0);
}

class _PopupMenuDefaultsM3 extends PopupMenuThemeData {
  _PopupMenuDefaultsM3(this.context) : super(elevation: 3.0);

  final BuildContext context;
  late final ThemeData _theme = Theme.of(context);
  late final ColorScheme _colors = _theme.colorScheme;
  late final TextTheme _textTheme = _theme.textTheme;

  @override
  WidgetStateProperty<TextStyle?>? get labelTextStyle {
    return WidgetStateProperty.resolveWith((Set<WidgetState> states) {
      final TextStyle style = _textTheme.labelLarge!;
      if (states.contains(WidgetState.disabled)) {
        return style.apply(color: _colors.onSurface.withValues(alpha: .38));
      }
      return style.apply(color: _colors.onSurface);
    });
  }

  @override
  Color? get color => _colors.surface;

  @override
  Color? get shadowColor => _colors.shadow;

  @override
  Color? get surfaceTintColor => _colors.surfaceTint;

  @override
  ShapeBorder? get shape => const RoundedRectangleBorder(
      borderRadius: BorderRadius.all(Radius.circular(4.0)));

  // Update this when the token is available.
  static EdgeInsets menuHorizontalPadding =
      const EdgeInsets.symmetric(horizontal: 12.0);
}
