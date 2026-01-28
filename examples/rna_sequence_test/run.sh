
 module load applications/gpu/python/conda-25.1.1-python-3.9.21  
 conda env list
 conda activate  ml-a  
 conda install -c bioconda bowtie2 

 echo "# Retreive small  small test dataset (E. coli)"
 echo wget https://ftp.ebi.ac.uk/vol1/fastq/SRR292/SRR292770/SRR292770_1.fastq.gz
 wget https://ftp.ebi.ac.uk/vol1/fastq/SRR292/SRR292770/SRR292770_1.fastq.gz

 echo wget https://ftp.ebi.ac.uk/vol1/fastq/SRR292/SRR292770/SRR292770_2.fastq.gz
 wget https://ftp.ebi.ac.uk/vol1/fastq/SRR292/SRR292770/SRR292770_2.fastq.gz

 echo "# Retreive E. coli reference genome "
 echo wget https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/005/845/GCF_000005845.2_ASM584v2/GCF_000005845.2_ASM584v2_genomic.fna.gz
 wget https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/005/845/GCF_000005845.2_ASM584v2/GCF_000005845.2_ASM584v2_genomic.fna.gz
 gunzip GCF_000005845.2_ASM584v2_genomic.fna.gz
 mv GCF_000005845.2_ASM584v2_genomic.fna ecoli_ref_v1.fa

 echo "#  create a second copy, Version 2: With artificial modification (simulates different patch)  "
 echo cp ecoli_ref_v1.fa ecoli_ref_v2.fa  
 cp ecoli_ref_v1.fa ecoli_ref_v2.fa  
 echo sed -i '1a >Modified_reference_version_2' ecoli_ref_v2.fa
 sed -i '1a >Modified_reference_version_2' ecoli_ref_v2.fa

 echo "# Test Case 1A: Correct Reference"

 echo "# Create input directory with CORRECT reference"
 echo mkdir -p test_A/inputs 
 mkdir -p test_A/inputs 
 echo cp SRR292770_*.fastq.gz test_A/inputs/
 cp SRR292770_*.fastq.gz test_A/inputs/
 echo cp ecoli_ref_v1.fa test_A/inputs/reference.fa
 cp ecoli_ref_v1.fa test_A/inputs/reference.fa
 echo cd test_A
 cd test_A
 echo "# Build bowtie index"
 echo bowtie2-build inputs/reference.fa inputs/ecoli_index  
 bowtie2-build inputs/reference.fa inputs/ecoli_index  

 echo "# Snapshot inputs"
 echo reprohash snapshot inputs/ -o input_snapshot.json 
 reprohash snapshot inputs/ -o input_snapshot.json 
 echo "# Run alignment"
 echo reprohash run   --input-hash "$(python3 -c "import json; print(json.load(open('input_snapshot.json'))['content_hash'])")"   --exec "bowtie2 -x inputs/ecoli_index -1 inputs/SRR292770_1.fastq.gz -2 inputs/SRR292770_2.fastq.gz -S alignment.sam"   --env-plugin pip   -o runrecord.json   --reproducibility-class deterministic  
 reprohash run   --input-hash "$(python3 -c "import json; print(json.load(open('input_snapshot.json'))['content_hash'])")"   --exec "bowtie2 -x inputs/ecoli_index -1 inputs/SRR292770_1.fastq.gz -2 inputs/SRR292770_2.fastq.gz -S alignment.sam"   --env-plugin pip   -o runrecord.json   --reproducibility-class deterministic  
 echo "# Create bundle"
 echo reprohash create-bundle   --input-snapshot input_snapshot.json   --runrecord runrecord.json   -o bundle
 reprohash create-bundle   --input-snapshot input_snapshot.json   --runrecord runrecord.json   -o bundle
 echo "# Verify"
 echo reprohash verify-bundle bundle/ -d inputs/
 reprohash verify-bundle bundle/ -d inputs/
 echo " "
 echo "# Test Case 1B: Wrong Reference (Simulates Common Error)"
 echo cd ../
 cd ../
 echo "# Create second test with WRONG reference"
 echo mkdir -p test_B/inputs
 mkdir -p test_B/inputs
 echo cp SRR292770_*.fastq.gz test_B/inputs/  
 cp SRR292770_*.fastq.gz test_B/inputs/  
 echo cp ecoli_ref_v2.fa test_B/inputs/reference.fa
 cp ecoli_ref_v2.fa test_B/inputs/reference.fa
 echo test_B
 cd test_B
 echo "# Try to verify with bundle from test_A"
 reprohash verify-bundle ../test_A/bundle/ -d inputs/ 
 cd ..
