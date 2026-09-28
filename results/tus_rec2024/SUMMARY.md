# TUS-REC2024 Pilot Summary

- Dataset: TUS-REC2024 Validation Dataset (subjects 050, 051, 052)
- DOI: `10.5281/zenodo.12979481`
- Archive: `Freehand_US_data_val.zip` (approximately 4.8 GB; MD5 `487ebe3241678569296e47efeb2ea325`)
- Scans validated: 72
- Validation failures: 0
- Reconstruction conditions run: 90
- Best non-reference raw union NRMSE: dropout_10pct on 050/RH_Per_S_DtP = 0.0039
- Worst non-reference raw union NRMSE: translation_noise_2mm on 052/RH_Par_L_DtP = 0.1267

`full_20fps` is a self-generated reconstruction reference using measured tracker poses; it is not anatomical ground truth.

This run validates the tracked geometric reconstruction pipeline. It does not validate Doppler blood flow or ALT perforator detection because those labels/modalities are not present in TUS-REC2024.
