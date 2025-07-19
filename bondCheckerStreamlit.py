import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import io
import docx  # For .docx files only

st.set_page_config(page_title="💵 Prize Bond Checker", layout="centered")

# --- Bond Type to URL Mapping ---
BOND_TYPES = {
    "Rs. 100": "https://savings.gov.pk/rs-100-prize-bond-draw/",
    "Rs. 200": "https://savings.gov.pk/rs-200-prize-bond-draw/",
    "Rs. 750": "https://savings.gov.pk/rs-750-prize-bond-draw/",
    "Rs. 1500": "https://savings.gov.pk/rs-1500-prize-bond-draw/",
    "Rs. 25000": "https://savings.gov.pk/premium-prize-bond-rs-25000/",
    "Rs. 40000": "https://savings.gov.pk/premium-prize-bond-rs-40000/"
}

# --- Hardcoded bond numbers for broken file ---
HARDCODED_BOND_URL = "First-Page-97th-draw-of-750-15-01-2024-1"                    
  
HARDCODED_BONDS = set([
    "125416", "164214", "344409", "081307", "149739", "320971", "075134",
    "259284", "181057", "298788", "290198", "325272", "164179", "291576",
    "071092", "085129", "339949", "106486", "142196", "327095", "051537",
    "330171", "056813", "339413", "251835", "331332", "061266", "147676",
    "222323", "317741", "172771", "080566", "343960", "104099", "206200",
    "058700", "263650", "313233", "147230", "230451", "052487", "051104",
    "297840", "320140", "297988", "198229", "283321", "205564", "158870",
    "118992", "084635", "244179", "261671", "331327", "163223", "184215",
    "148108", "160317", "254003", "162721", "260788", "288201", "088041",
    "162282", "327770", "120723", "120771", "221348", "081567", "153771",
    "341914", "142030", "129208", "159648", "069439", "329574", "336335",
    "060622", "146420", "343781", "221029", "167164", "265778", "060258",
    "150914", "228881", "064402", "095738", "295905", "288610", "068061",
    "105319", "341362", "149980", "155281", "329070", "102570", "336764",
    "073203", "290719", "287409", "117180", "153365", "329939", "203920"
])

# --- Extract Bond Numbers from text ---
def extract_bond_numbers(text):
    return set(re.findall(r'\b\d{6}\b', text))

# --- Fetch Result Files ---
@st.cache_data(show_spinner="📥 Fetching result files...")
def fetch_result_files(bond_type_url, bond_type):
    response = requests.get(bond_type_url)
    soup = BeautifulSoup(response.text, "html.parser")
    file_links = soup.find_all("a", href=re.compile(r'\.(txt|docx?)$'))

    result_files = []
    for link in file_links:
        file_url = link["href"]
        if not file_url.startswith("http"):
            file_url = "https://savings.gov.pk" + file_url
        result_files.append(file_url)

    # Append fallback for Rs. 750
    if bond_type == "Rs. 750":
        result_files.append(HARDCODED_BOND_URL)

    st.write(f"📂 Found {len(result_files)} result file(s).")
    return result_files

# --- Reset flag ---
if "reset" not in st.session_state:
    st.session_state.reset = False

def reset_app():
    st.session_state.reset = True

# --- UI ---
st.title("💵 Prize Bond Checker")
st.markdown("Upload your bond list and check if you've hit the jackpot. 🎯")

st.markdown("---")
if st.button("🔎 Check on Official Website"):
    st.markdown("[Go to Official Prize Bond Checker](https://www.savings.gov.pk/latest/results.php#focus)", unsafe_allow_html=True)

# --- Main Logic ---
if not st.session_state.reset:
    bond_type = st.selectbox("Select bond type", list(BOND_TYPES.keys()))
    bond_file = st.file_uploader("📤 Upload your bond list (.txt)", type=["txt"])

    if bond_file and bond_type:
        try:
            user_bonds = set(
                line.strip().decode("utf-8") for line in bond_file if re.fullmatch(rb'\d{6}', line.strip())
            )

            if not user_bonds:
                st.warning("⚠️ No valid 6-digit bond numbers found in your file.")
            else:
                result_files = fetch_result_files(BOND_TYPES[bond_type], bond_type)
                matched_bonds = set()
                matches_by_file = {}

                for file_url in result_files:
                    try:
                        if file_url == HARDCODED_BOND_URL:
                            winning_bonds = HARDCODED_BONDS
                            content_label = "Hardcoded Result (750 - Jan 2024)"

                        elif file_url.endswith(".txt"):
                            content = requests.get(file_url).text
                            winning_bonds = extract_bond_numbers(content)
                            content_label = file_url.split("/")[-1]

                        elif file_url.endswith(".docx"):
                            doc = docx.Document(io.BytesIO(requests.get(file_url).content))
                            content = "\n".join([para.text for para in doc.paragraphs])
                            winning_bonds = extract_bond_numbers(content)
                            content_label = file_url.split("/")[-1]

                        else:
                            continue  # Skip .doc files or unsupported types

                        matches = user_bonds & winning_bonds

                        if matches:
                            matches_by_file[content_label] = sorted(matches)
                            matched_bonds.update(matches)

                    except Exception as e:
                        st.warning(f"⚠️ Skipped file due to error: {file_url} - {e}")
                        continue

                if matches_by_file:
                    st.success("🎉 You've got some winners!")
                    for file, bonds in matches_by_file.items():
                        st.markdown(f"**📄 {file}**")
                        for bond in bonds:
                            st.markdown(f"- 🏅 **{bond}**")
                        st.markdown("---")

                    output = io.StringIO()
                    output.write("Winning Bonds:\n")
                    for bond in sorted(matched_bonds):
                        output.write(f"{bond}\n")
                    output.seek(0)

                    st.download_button(
                        label="⬇️ Download Winning Bonds (.txt)",
                        data=output.getvalue(),
                        file_name="winning_bonds.txt",
                        mime="text/plain"
                    )
                else:
                    st.info("🙃 No winning bonds found in recent draws.")

                st.button("🔁 Check Another Bond Type", on_click=reset_app)

        except Exception as e:
            st.error(f"❌ Something went wrong: {e}")
else:
    st.session_state.reset = False
    st.rerun()
