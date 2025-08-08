Option 1: Download the PDF locally first, then upload via curl
Download the PDF locally:
wget https://github.com/mohamadmonzer-a/railwayBackend/raw/main/Final_amended_after_printing_EN_PHC_Guide_September_25_2c_2015.pdf -O myfile.pdf

Then run your curl upload with the downloaded file:
curl -X POST "https://web-production-5be1.up.railway.app/upload_pdf/" \
  -F "file=@myfile.pdf" \
  -F "session_id=testsession123"
