# PROJECT: Django Application System – Recruitment Platform (UPDATED v8)

## OVERVIEW

Arabic RTL recruitment platform for managing applications to:
→ jobs + senior positions

Public terminology:
- وظائف عليا
- مناصب عليا
- رتب

Internal poste_type:
- transfer
- detachment
- head_office

System split:
1. PUBLIC (candidate side)
2. ADMIN (management side)

No authentication required for candidates.

Tracking is handled via:
- tracking_code
- direct tracking link
- QR code

Notifications handled via:
- NotificationService
- NotificationLog
- email templates
- Celery async queue

---

## CURRENT STATE

✔ End-to-end workflow fully functional  
✔ Public UX unified across all steps  
✔ Select2 integrated for poste selection  
✔ Wilaya/Commune dynamic loading stabilized  
✔ Upload system (auto + manual) improved  
✔ Review page redesigned (clean + decision-oriented)  
✔ Final submission secured with confirmation modal  
✔ Success page enhanced (tracking + QR + PDF)  
✔ Tracking pages improved (timeline + clarity)  
✔ Email templates unified (official style)  
✔ Notification logging implemented  
✔ Admin partially refined  
✔ django-import-export integrated  
✔ Legal references DB-driven  

Current phase:
→ admin refinement + data consistency + production hardening

---

## APPLICATION FLOW (FINAL)

1. start_application  
2. candidate_information  
3. motivation_step  
4. upload_documents  
5. review_application  
6. submit_application  
7. success  
8. tracking  

---

## SESSION LOGIC

Session-driven flow:

- selected_poste_id
- selected_poste_ids (multi-choice)
- candidate_id
- draft_application_id

Rules:
- only one active draft per session
- no return after submission
- session cleared after final submit

---

## POSTE SELECTION

✔ Multi-choice (1–3 ordered priorities)  
✔ Select2 enabled (searchable dropdown)  
✔ Duplicate selection prevented (JS + backend)  
✔ Slug-based routing supported  

---

## CANDIDATE PROFILE

Validated fields:
- personal identity (NIN 18 digits, unique)
- contact information
- address (wilaya → commune)
- professional data

Enhancements:
- Arabic-only validation (front + backend)
- placeholders and helper texts
- numeric input sanitization
- date constraints

---

## MOTIVATION STEP

✔ Mandatory before proceeding  
✔ Word count validation (100–500)  
✔ Real-time feedback + progress bar  
✔ Prevent submission if invalid  
✔ Stored in draft application  

---

## DOCUMENT UPLOAD

✔ Requirement-based upload system  
✔ Supports:
- auto upload
- manual upload
- replacement

✔ Real-time validation:
- file size
- format
- requirement constraints

✔ Missing documents detection before review

---

## REVIEW PAGE (CRITICAL)

Final decision screen before submission.

Displays:
- ordered postes (priorities)
- motivation (scroll-safe container)
- candidate summary (compact grid)
- documents status (complete / missing)

Enhancements:
- clean layout (reduced vertical length)
- official UI alignment
- sidebar with final instructions
- progress visualization

---

## FINAL SUBMISSION

✔ Allowed only if:
- status = DRAFT
- all required documents uploaded

✔ Confirmation modal required before submit

✔ Submit flow:
- user clicks "الإرسال النهائي"
- modal appears
- user confirms
- POST request sent

✔ Protections:
- no nested forms
- single submission endpoint
- double submit prevention

---

## SUBMISSION RESULT

On submit:

- status → SUBMITTED
- application_number generated
- tracking_code generated
- tracking entry created
- session cleared

Notifications:
- candidate confirmation email
- admin notification email

---

## SUCCESS PAGE

Displays:
- application number
- tracking code
- primary poste
- QR code
- PDF receipt
- direct tracking link

UX:
- clear next steps
- copy tracking code
- official tone

---

## TRACKING SYSTEM

No authentication required.

User can:
- view status
- see timeline
- see rejection reason (if allowed)

UX improvements:
- structured timeline
- clear status labels
- strong readability

---

## ADMIN SIDE

Current direction:
→ evaluation-ready system

Implemented:
- improved PosteAdmin
- LegalReferenceAdmin
- NotificationLogAdmin
- import/export workflows

Next:
- application evaluation UI
- scoring system (planned)
- filtering + monitoring tools

---

## LEGAL REFERENCES

Managed from DB.

Fields:
- title
- reference_number
- reference_type
- published_date
- description
- document_url
- is_active
- display_order

Rules:
- only active references shown
- no empty categories
- sorted properly

---

## NOTIFICATION SYSTEM

- NotificationService (central logic)
- NotificationLog (tracking)
- Celery async sending

Templates:
- application_submitted
- status_update
- interview_scheduled
- admin_new_application

Design:
- Arabic RTL
- official branding
- unified layout

---

## UI PRINCIPLES

- clean
- minimal
- official (ministry-style)
- Arabic RTL
- consistent across pages

No unnecessary redesign allowed.

---

## CRITICAL RULES

- no multiple active applications (NIN rule)
- motivation required before upload
- review is display-only
- submission only via submit_application
- no return after submission
- no duplicate notifications

---

## CURRENT FOCUS

- admin refinement
- data consistency
- notification monitoring
- production readiness
- evaluation system preparation

---

END v8