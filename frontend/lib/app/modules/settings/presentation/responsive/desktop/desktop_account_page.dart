import 'package:flutter/material.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_file_selector.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:file_picker/file_picker.dart';

class Profile {
  final int id;
  final int user;
  final bool emailVerified;
  final String fullName;
  final String email;
  final String dateOfBirth;
  final String phoneNumber;
  final String physicalAddress;
  final String walletBalance;

  Profile({
    required this.id,
    required this.user,
    required this.emailVerified,
    required this.fullName,
    required this.email,
    required this.dateOfBirth,
    required this.phoneNumber,
    required this.physicalAddress,
    required this.walletBalance,
  });
}

class DesktopAccountPage extends StatefulWidget {
  const DesktopAccountPage({super.key});

  @override
  State<DesktopAccountPage> createState() => _DesktopAccountPageState();
}

class _DesktopAccountPageState extends State<DesktopAccountPage> {
  Profile? userProfile;
  String? kycStatus;
  String? kycSubmittedDate;
  String? reviewerComment;
  ExistingFile? userAvatar;

  @override
  void initState() {
    super.initState();
    _loadUserProfile();
  }

  Future<void> _loadUserProfile() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');
    final headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };

    final response = await http.get(
      Uri.parse('https://api.bbbprediction.com/users/profile/'),
      headers: headers,
    );

    print("User Profile Details");
    print(response.body);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final profile = data['profile'];
      final kyc = data['kyc_profile'];

      String formattedDob = _formatDate(profile['date_of_birth']);
      String formattedKycDate = _formatDate(kyc?['submitted_at']);

      setState(() {
        userProfile = Profile(
          id: profile['id'],
          user: profile['user'],
          emailVerified: profile['email_verified'],
          fullName: profile['full_name'] ?? "N/A",
          email: profile['email'] ?? "N/A",
          dateOfBirth: formattedDob,
          phoneNumber: profile['phone_number'] ?? "N/A",
          physicalAddress: profile['physical_address'] ?? "N/A",
          walletBalance: profile['wallet_balance'] ?? "N/A",
        );
        kycStatus = kyc?['kyc_status'] ?? "N/A";
        kycSubmittedDate = formattedKycDate;
        reviewerComment = kyc?['reviewer_comment'] ?? "";
      });
    }
  }

  String _formatDate(String? raw) {
    if (raw == null || !raw.contains('-')) return "N/A";
    final datePart = raw.split('T')[0];
    final parts = datePart.split('-');
    return parts.length == 3 ? "${parts[1]}-${parts[2]}-${parts[0]}" : raw;
  }

  Future<void> uploadKycWithDocumentAndSelfie({
    required BuildContext context,
    required PlatformFile idDocFile,
    required PlatformFile selfieFile,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');

    final uri = Uri.parse("https://api.bbbprediction.com/users/mykyc/upload/");
    final request = http.MultipartRequest('PATCH', uri);
    request.headers['Authorization'] = 'Bearer $token';

    request.files.add(
      http.MultipartFile.fromBytes(
        'id_document',
        idDocFile.bytes!,
        filename: idDocFile.name,
      ),
    );

    request.files.add(
      http.MultipartFile.fromBytes(
        'selfie_image',
        selfieFile.bytes!,
        filename: selfieFile.name,
      ),
    );

    final response = await request.send();
    final responseBody = await response.stream.bytesToString();

    print("KYC Upload Status: ${response.statusCode}");
    print("KYC Upload Response: $responseBody");

    _loadUserProfile();

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text("Document uploaded successfully ✅"),
        backgroundColor: Colors.green,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  void showKycUploadDialog(BuildContext context) {
    PlatformFile? idDocFile;
    PlatformFile? selfieFile;

    showDialog(
      context: context,
      barrierDismissible: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            final dialogWidth = MediaQuery.of(context).size.width < 420
                ? MediaQuery.of(context).size.width - 32
                : 420.0;
            return Dialog(
              insetPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 24,
              ),
              backgroundColor: const Color(0xFF0d1117),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: dialogWidth),
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text(
                        "Upload KYC Documents",
                        style: TextStyle(color: Colors.white, fontSize: 18),
                      ),
                      const SizedBox(height: 20),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: const Color(0xFF0d1117),
                          ),
                          onPressed: () async {
                            final result = await FilePicker.platform.pickFiles(
                              withData: true,
                              type: FileType.custom,
                              allowedExtensions: [
                                'pdf',
                                'jpg',
                                'png',
                                'doc',
                                'docx',
                              ],
                            );
                            if (result != null) {
                              setState(() => idDocFile = result.files.single);
                            }
                          },
                          child: Text(
                            idDocFile == null
                                ? "Select ID Document"
                                : "ID Document Selected",
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: const Color(0xFF0d1117),
                          ),
                          onPressed: () async {
                            final result = await FilePicker.platform.pickFiles(
                              withData: true,
                              type: FileType.image,
                            );
                            if (result != null) {
                              setState(() => selfieFile = result.files.single);
                            }
                          },
                          child: Text(
                            selfieFile == null
                                ? "Select Selfie Image"
                                : "Selfie Image Selected",
                          ),
                        ),
                      ),
                      const SizedBox(height: 24),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.green,
                            foregroundColor: Colors.white,
                          ),
                          onPressed: (idDocFile != null && selfieFile != null)
                              ? () async {
                                  Navigator.of(context).pop();
                                  await uploadKycWithDocumentAndSelfie(
                                    context: context,
                                    idDocFile: idDocFile!,
                                    selfieFile: selfieFile!,
                                  );
                                }
                              : null,
                          child: const Text("Submit KYC"),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final userData = userProfile == null
        ? []
        : [
            ('Full name', userProfile!.fullName),
            ('Date of Birth', userProfile!.dateOfBirth),
            ('Email address', userProfile!.email),
            ('Phone number', userProfile!.phoneNumber),
            ('Address', userProfile!.physicalAddress),
            if (kycStatus != null) ('KYC Status', kycStatus!),
            if (kycSubmittedDate != null)
              ('KYC Submitted Date', kycSubmittedDate!),
            if ((kycStatus == "pending" || kycStatus == "rejected") &&
                reviewerComment != null &&
                reviewerComment!.isNotEmpty)
              ('Reviewer Comment', reviewerComment!),
          ];

    return Container(
      color: const Color(0xFF0d1117), // full background
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Account",
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 40),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: const [
                Text(
                  "Personal Details",
                  style: TextStyle(fontSize: 16, color: Colors.white),
                ),
                // Keep the button styled as is
              ],
            ),
            const SizedBox(height: 16),
            CustomDivider(),
            const SizedBox(height: 24),
            if (userProfile == null)
              const Center(child: CircularProgressIndicator())
            else
              ...userData.map(
                (item) => Column(
                  children: [
                    ListTile(
                      title: Text(
                        item.$1,
                        style: const TextStyle(
                          fontSize: 12,
                          color: Colors.white,
                        ),
                      ),
                      subtitle: Text(
                        item.$2,
                        style: const TextStyle(
                          fontSize: 16,
                          color: Colors.white,
                        ),
                      ),
                      trailing: const Icon(
                        Icons.arrow_forward_ios,
                        size: 14,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 12),
                  ],
                ),
              ),
            if (kycStatus == "pending" || kycStatus == "rejected")
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: CustomOutlinedButton.big(
                  text: 'Upload KYC',
                  onTap: () => showKycUploadDialog(context),
                ),
              ),
            const SizedBox(height: 24),
            const Text(
              "Profile Picture",
              style: TextStyle(fontSize: 16, color: Colors.white),
            ),
            const SizedBox(height: 12),
            CustomDivider(),
            const SizedBox(height: 24),
            CustomFileSelector(
              existingFile: userAvatar,
              onFileSelected: (file) {
                setState(() {
                  userAvatar = file;
                });
              },
            ),
          ],
        ),
      ),
    );
  }
}
