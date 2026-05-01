import 'package:country_code_picker/country_code_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/domain/repositories/auth_repository.dart';
import 'package:frontend/app/modules/auth/presentation/providers/signup_dto_notifier.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/login_dialog.dart';
import 'package:frontend/app/shared/classes/helpers/debouncer.dart';
import 'package:frontend/app/shared/extensions/string_extension.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_textfield.dart';
import 'package:frontend/app/shared/presentation/widgets/title_subtitle.dart';
import 'package:frontend/core/framework/theme/colors/app_colors.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/core/navigation/navigator.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';
class CreateAccountStep2 extends ConsumerStatefulWidget {
  const CreateAccountStep2({
    super.key,
    this.onBack,
  });

  final VoidCallback? onBack;

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _CreateAccountStep2State();
}

class _CreateAccountStep2State extends ConsumerState<CreateAccountStep2> {
  String dialCode = '+44';
  bool enterAddressManually = true;
  String query = '';
  bool showSuggestions = false;
  final TextEditingController _addressController = TextEditingController();
  final FocusNode _addressFocusNode = FocusNode();
  late ScrollController _scrollController;  // Add scroll controller

  final _debouncer = Debouncer(duration: const Duration(milliseconds: 300));

  // // Dummy address data for autocomplete
  // final List<String> _addressSuggestions = [
  //   "42 Meadow Lane, Hammersmith, London, TW4 5EZ",
  //   "15 Oakfield Crescent, Edgbaston, Birmingham, B15 3TT",
  //   "38 St. George's Road, Brighton, BN2 1EL",
  //   "3 Willow Bank Close, Headingley, Leeds, LS6 2HW",
  //   "29 Church Street, Ancoats, Manchester, M4 6PG",
  //   "71 Rosewood Avenue, Clifton, Bristol, BS8 2NA4",
  //   "8 Victoria Gardens, Bath, BA1 5LH",
  //   "156 High Street, Canterbury, Kent, CT1 2JE",
  //   "22 Park Lane, Windsor, Berkshire, SL4 1LR",
  //   "67 Mill Road, Cambridge, CB1 3DP",
  //   "14 Queen's Drive, Edinburgh, EH4 2BN",
  //   "91 Castle Street, Cardiff, CF10 1BU",
  //   "33 Harbour View, Plymouth, PL1 3DE",
  //   "45 Oak Tree Lane, Nottingham, NG1 5DT",
  //   "78 Rose Garden Way, Oxford, OX1 2HF"
  // ];

  @override
  void initState() {
    super.initState();
    // Initialize scroll controller
    _scrollController = ScrollController();
    
    // Scroll to top after first frame is rendered
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.jumpTo(0.0);
      }
    });
    
    _addressFocusNode.addListener(() {
      if (!_addressFocusNode.hasFocus) {
        // Hide suggestions when focus is lost
        setState(() {
          showSuggestions = false;
        });
      }
    });

    _addressController.addListener(() {
      setState(() {});
    });
  }

  @override
  void dispose() {
    _addressController.dispose();
    _addressFocusNode.dispose();
    _scrollController.dispose();  // Dispose scroll controller
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final dto = ref.watch(signupDtoProvider);
    final notifier = ref.read(signupDtoProvider.notifier);

    return SingleChildScrollView(
      controller: _scrollController,  // Add scroll controller
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (widget.onBack != null) ...[
            Clickable(
              onClick: widget.onBack,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.arrow_back_ios_new,
                    size: 14,
                    color: colors.alwaysWhite,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Back',
                    style: _getTextStyle(colors, fontSize: 14).copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
          ],
          Center(
            child: TitleSubtitle(
              title: 'Contact Details',
              subtitle: 'Provide contact details so we can reach you.',
            ),
          ),
        const SizedBox(height: 44),
        CustomTextField(
          headerText: 'Email address',
          hint: 'jane.doe@example.com',
          keyboardType: TextInputType.emailAddress,
          onChanged: notifier.setEmail,
        ),
        const SizedBox(height: 24),
        Text(
          "Phone number",
          style: _getTextStyle(colors, fontSize: 14),
        ),
        const SizedBox(height: 6),
        Row(
          children: [
            Expanded(
              flex: 1,
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 5),
                decoration: BoxDecoration(
                  color: colors.always30363D.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: colors.always30363D, width: 1),
                ),
                child: CountryCodePicker(
                  onChanged: (country) {
                    setState(() => dialCode = country.dialCode!);
                  },
                  initialSelection: 'GB',
                  favorite: [  ],
                  showCountryOnly: false,
                  showOnlyCountryWhenClosed: false,
                  alignLeft: false,
                  searchStyle: _getTextStyle(colors),
                  dialogSize: const Size(400, 400),
                  dialogBackgroundColor: colors.primary,
                  headerTextStyle: _getTextStyle(colors),
                  dialogTextStyle: _getTextStyle(colors),
                  textStyle: _getTextStyle(colors),
                  barrierColor: colors.transparent,
                  boxDecoration: BoxDecoration(
                    border: Border.all(
                      color: colors.always30363D.withValues(alpha: 0.3),
                    ),
                    borderRadius: BorderRadius.circular(8),
                    color: colors.primary,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              flex: 3,
              child: CustomTextField(
                hint: 'Enter your phone number',
                keyboardType: TextInputType.phone,
                onChanged: (v) {
                  final phone = "$dialCode$v";
                  notifier.setPhone(phone);
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
        if (enterAddressManually) ...[
          CustomTextField(
            headerText: 'Current address',
            hint: 'Enter your street address',
            onChanged: notifier.setCurrentAddress,
          ),
          const SizedBox(height: 24),
          CustomTextField(
            headerText: 'ZIP/Postal Code',
            hint: 'Enter your zip/postal code',
            onChanged: notifier.setPostalCode,
            // inputFormatters: [
            //   FilteringTextInputFormatter.digitsOnly,
            // ],
          ),
          const SizedBox(height: 24),
          CustomTextField(
            headerText: 'City',
            hint: 'Enter the city you live in',
            onChanged: notifier.setCity,
          ),
          // const SizedBox(height: 24),
          // Clickable(
          //   onClick: () {
          //     setState(() {
          //       enterAddressManually = false;
          //     });
          //   },
          //   child: Center(
          //     child: Text(
          //       'Use address search instead',
          //       style: _getTextStyle(colors).copyWith(
          //         decoration: TextDecoration.underline,
          //       ),
          //     ),
          //   ),
          // ),
          const SizedBox(height: 44),
        ] else ...[
          // CustomTextField(
          //   headerText: 'Home address',
          //   hint: 'Start typing your address...',
          //   textEditingController: _addressController,
          //   node: _addressFocusNode,
          //   onChanged: (value) {
          //     notifier.setCurrentAddress(value);
          //     _debouncer.run(() {
          //       setState(() {
          //         query = value;
          //         showSuggestions = value.isNotEmpty && value.length >= 2;
          //       });
          //     });
          //   },
          // ),
          // Inline suggestions dropdown
          //   if (showSuggestions) ...[
          //     const SizedBox(height: 12),
          //     _buildSuggestionsDropdown(
          //       colors,
          //       notifier.setCurrentAddress,
          //     ),
          //   ],
          //   SizedBox(height: 24), // Dynamic spacing
          //   Clickable(
          //     onClick: () {
          //       setState(() {
          //         enterAddressManually = true;
          //         showSuggestions = false;
          //         _addressController.clear();
          //       });
          //     },
          //     child: Center(
          //       child: Text(
          //         'Enter address manually instead',
          //         style: _getTextStyle(colors).copyWith(
          //           decoration: TextDecoration.underline,
          //         ),
          //       ),
          //     ),
          //   ),
          //   const SizedBox(height: 44),
        ],
        CustomButton(
          text: 'Create account',
          onPressed: () {
            final repo = ref.read(authRepositoryProvider);
            perform(
              context,
              response: repo.signup(dto: dto),
              onSuccess: (_) {
                // popAndShowCenterDialog(context, LoginDialog());
                final repo = ref.read(authRepositoryProvider);
              perform(
                context,
                response: repo.login(username: dto.username, password: dto.password),
                onSuccess: (d)async {
                   
                  ref.read(currentUserProvider.notifier).state = d.profile;
                  // popAndShowCenterDialog(
                  //   context,
                  //   VerifyAccountDialog(),
                  // );
                  // Save in SharedPreferences
                    final prefs = await SharedPreferences.getInstance();
                    prefs.setInt('user_id', d.profile.user);
                    prefs.setBool('email_verified', d.profile.emailVerified);
                    prefs.setInt('profile_id', d.profile.id);
                    prefs.setString('access_token', d.access);
                    print("Chethan TOken");
                    print(d.access);
                    prefs.setString('refresh_token', d.refresh);

                    // 🔽 Save additional profile fields
                    prefs.setString('full_name', d.profile.fullName);
                    prefs.setString('email', d.profile.email);
                    prefs.setString('date_of_birth', d.profile.dateOfBirth);
                    prefs.setString('phone_number', d.profile.phoneNumber);
                    prefs.setString('physical_address', d.profile.physicalAddress);
                  pop(context);
                },
              );
              },
            );
          },
          validator: () {
            return dto.email.isValidEmail() &&
                dto.currentAddress.isNotEmptyAndLongerThan5;
          },
        ),
        const SizedBox(height: 24),
      ],
    ),
  );
  }

  // Widget _buildSuggestionsDropdown(
  //   AppColors colors,
  //   Function(String) setAddress,
  // ) {
  //   // Filter addresses based on query
  //   final filteredAddresses = _addressSuggestions
  //       .where((address) => address.toLowerCase().contains(query.toLowerCase()))
  //       .take(5)
  //       .toList();

  //   if (filteredAddresses.isEmpty) return const SizedBox.shrink();

  //   return Material(
  //     elevation: 8,
  //     borderRadius: BorderRadius.circular(8),
  //     color: colors.primary,
  //     child: Container(
  //       constraints: BoxConstraints(maxHeight: 200),
  //       decoration: BoxDecoration(
  //         color: colors.primary,
  //         borderRadius: BorderRadius.circular(8),
  //         border: Border.all(
  //           color: colors.always30363D.withValues(alpha: 0.3),
  //         ),
  //       ),
  //       child: ListView.separated(
  //         shrinkWrap: true,
  //         padding: const EdgeInsets.symmetric(vertical: 8),
  //         itemCount: filteredAddresses.length,
  //         separatorBuilder: (context, index) => Divider(
  //           color: colors.always30363D.withValues(alpha: 0.2),
  //           height: 1,
  //           indent: 16,
  //           endIndent: 16,
  //         ),
  //         itemBuilder: (context, index) {
  //           final address = filteredAddresses[index];
  //           return Clickable(
  //             onClick: () {
  //               setAddress(address);
  //               setState(() {
  //                 showSuggestions = false;
  //                 query = address;
  //                 _addressController.text = address;
  //               });
  //               _addressFocusNode.unfocus();
  //             },
  //             child: Container(
  //               padding: const EdgeInsets.symmetric(
  //                 horizontal: 16,
  //                 vertical: 12,
  //               ),
  //               child: Row(
  //                 children: [
  //                   Icon(
  //                     Icons.location_on_outlined,
  //                     size: 18,
  //                     color: colors.alwaysWhite.withValues(alpha: 0.7),
  //                   ),
  //                   const SizedBox(width: 12),
  //                   Expanded(
  //                     child: Text(
  //                       address,
  //                       style: _getTextStyle(colors).copyWith(
  //                         fontSize: 13,
  //                         fontWeight: FontWeight.w400,
  //                         color: colors.alwaysWhite,
  //                       ),
  //                     ),
  //                   ),
  //                 ],
  //               ),
  //             ),
  //           );
  //         },
  //       ),
  //     ),
  //   );
  // }

  TextStyle _getTextStyle(AppColors colors, {double? fontSize = 12}) {
    return TextStyle(
      color: colors.alwaysWhite,
      fontSize: fontSize,
      fontWeight: FontWeight.w300,
    );
  }
}
