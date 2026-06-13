# PrecipQC
A self-contained offline web application for **precipitation gauge image validation and data quality control**.

Built for field hydrology / meteorology workflows: match CSV spreadsheet readings against gauge photos, flag records as Match / Unsure / Wrong, input corrected values, and export cleaned results automatically.

## Key Features
- Fully offline browser-based tool (no server, no installation required)
- Compare readings from cup guage, tipping bucket gauge and image of cup guage reading on the same screen
- Image zoom/pan for close inspection of gauge photos
- Keyboard shortcuts for fast workflow (1 = Match, 2 = Unsure, 3 = Wrong, Enter = Confirm)
- Export outputs:
  - Cleaned validated CSV, data you are confident to use for your analysis
  - Summary statistics CSV by station, for follow-up on data quality issues
  - Structured JSON review log with notes & corrected values, for potential training of AI tools

## How to Use
1. Download `PrecipQC_v5.html` and open it in Google Chrome
2. Load your gauge CSV file
3. (Optional) Load tipping bucket CSV
4. Select your local image folder
5. Choose start / end date range
6. Start review: inspect images, assign quality labels, add corrections/notes
7. When finished: End & Export all output files

## User Manual
Full detailed step-by-step user guide [here](https://github.com/Doriswong35/precip-qc/blob/main/precip_qcv5_manual_1.1.pdf)

## Tech Stack
- Pure HTML / CSS / Vanilla JavaScript
- No frameworks, no dependencies
- Runs entirely locally in your browser (all files stay on your computer, no data uploaded anywhere)

## Privacy
All data, images, and exported files remain **local on your device**. No data is sent to any server.

## License
Free for personal, research, and non-commercial use.
