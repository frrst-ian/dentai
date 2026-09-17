# DentAI Dental – Patient Dental Chart Module

This package extends the supplied Flask prototype with a functional **Dental Chart & Patient Records** module.

## Added functionality
- Patient profile page with demographics and clinical summary
- Interactive FDI dental chart (11–48, excluding 55–85 primary teeth in this version)
- Tooth status per tooth: Healthy, Caries, Filled, Missing, Extracted, Root Canal, Crown, Implant, Impacted
- Tooth notes and last-updated timestamp
- Treatment/clinical record history per patient
- Add new treatment record
- Quick navigation from patient list to Dental Chart
- Database migration that creates `tooth_records` and `treatment_records` without deleting existing patient/appointment data

## Run
1. Put the folder in your working directory.
2. Install dependencies: `pip install -r requirements.txt`
3. Run `run.bat` or `python app.py`
4. Open http://127.0.0.1:5000

This remains an academic prototype. Clinical records should only use authorized data, with appropriate security, privacy, access control, backup, and clinical validation before real deployment.


## Integrated Patient Modules
From the Patients page, each patient now has direct access to:
- 🦷 Dental Chart
- 📋 Clinical Records
- 🤖 AI Prediction
The AI Prediction page automatically loads the selected patient's current clinical data before running the selected model.
