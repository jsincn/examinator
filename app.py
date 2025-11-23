import streamlit as st
import time
import json
import tempfile
import os
from data_model import (
    Exam,
    ExamContent,
    ExamQuestion,
    SubQuestion,
    MultipleChoiceExamQuestion,
    MultipleChoiceSubQuestion,
)
from build_exam import build_exam
from dotenv import load_dotenv
from build_new_mp_questions import generate_exam_question_with_openai
from ragpipeline import ingest_script_for_rag

from ensemble_solver import EnsembleCoordinator
from parsing_new import parse_exam_complete

load_dotenv()

# Initialize session state
if "run_workflow" not in st.session_state:
    st.session_state["run_workflow"] = False
if "exam_built" not in st.session_state:
    st.session_state["exam_built"] = False
if "use_rag" not in st.session_state:
    st.session_state["use_rag"] = False

# Configure page
st.set_page_config(
    layout="wide",
    page_title="Examinator - Exam Builder",
    page_icon="📝",
    initial_sidebar_state="collapsed"
)

# Header - Clean Apple style
st.markdown("""
    <div class="header-container" style="text-align: center; padding: 0.5rem 0 2rem 0; margin-bottom: 2rem;">
    <h1 class="header-title" style="margin: 0; font-size: 2.5rem; font-weight: 700; letter-spacing: -0.02em; color: #0065BD;">Examinator</h1>
    <p class="header-intro" style="margin: 1.5rem auto 0 auto; max-width: 600px; font-size: 0.9375rem; font-weight: 400; line-height: 1.5; color: #6e6e73;">Create realistic mock exams for students that match the format, length, and complexity of actual old exams. Upload past exam PDFs to generate practice tests that mirror what professors typically hand out.</p>
</div>
""", unsafe_allow_html=True)

# Custom CSS - Clean Apple-like Design
st.markdown("""
<style>
    /* Apple-like clean design - Dark mode compatible */
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    }
    
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* CSS Variables for theme-aware colors */
    :root {
        --header-subtitle-color: rgba(255, 255, 255, 0.6);
        --header-intro-color: rgba(255, 255, 255, 0.7);
    }
    
    .stApp[data-theme="light"] {
        --header-subtitle-color: #86868b;
        --header-intro-color: #6e6e73;
    }
    
    /* Theme-adaptive header colors */
    .header-title {
        color: #0065BD !important; /* TUM Blue - always */
    }
    
    .header-subtitle {
        color: var(--header-subtitle-color) !important;
    }
    
    /* Header intro - default to dark mode */
    .header-intro {
        color: rgba(255, 255, 255, 0.7) !important;
    }
    
    /* Light mode header intro - multiple selector strategies */
    .stApp[data-theme="light"] .header-intro,
    [data-theme="light"] .header-intro,
    .stApp:not([data-theme="dark"]) .header-intro {
        color: #6e6e73 !important;
    }
    
    /* Dark mode override (more specific) */
    .stApp[data-theme="dark"] .header-intro,
    [data-theme="dark"] .header-intro {
        color: rgba(255, 255, 255, 0.7) !important;
    }
    
    /* Exam details theme adaptation - default to dark mode */
    .exam-details-container {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: rgba(255, 255, 255, 0.9) !important;
    }
    
    .exam-details-value {
        color: rgba(255, 255, 255, 0.9) !important;
    }
    
    .exam-details-label {
        color: rgba(255, 255, 255, 0.6) !important;
    }
    
    /* Dark mode exam details */
    .stApp[data-theme="dark"] .exam-details-container,
    [data-theme="dark"] .exam-details-container {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: rgba(255, 255, 255, 0.9) !important;
    }
    
    .stApp[data-theme="dark"] .exam-details-container .exam-details-value,
    [data-theme="dark"] .exam-details-container .exam-details-value,
    .stApp[data-theme="dark"] .exam-details-container span.exam-details-value,
    [data-theme="dark"] .exam-details-container span.exam-details-value,
    .stApp[data-theme="dark"] .exam-details-value,
    [data-theme="dark"] .exam-details-value {
        color: rgba(255, 255, 255, 0.9) !important;
    }
    
    .stApp[data-theme="dark"] .exam-details-container .exam-details-label,
    [data-theme="dark"] .exam-details-container .exam-details-label,
    .stApp[data-theme="dark"] .exam-details-container strong.exam-details-label,
    [data-theme="dark"] .exam-details-container strong.exam-details-label,
    .stApp[data-theme="dark"] .exam-details-label,
    [data-theme="dark"] .exam-details-label {
        color: rgba(255, 255, 255, 0.6) !important;
    }
    
    /* Light mode exam details - multiple selector strategies */
    .stApp[data-theme="light"] .exam-details-container,
    [data-theme="light"] .exam-details-container,
    .stApp:not([data-theme="dark"]) .exam-details-container {
        background: rgba(0, 0, 0, 0.03) !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        color: #1d1d1f !important;
    }
    
    .stApp[data-theme="light"] .exam-details-container .exam-details-value,
    [data-theme="light"] .exam-details-container .exam-details-value,
    .stApp[data-theme="light"] .exam-details-container span.exam-details-value,
    [data-theme="light"] .exam-details-container span.exam-details-value,
    .stApp[data-theme="light"] .exam-details-value,
    [data-theme="light"] .exam-details-value,
    .stApp:not([data-theme="dark"]) .exam-details-container .exam-details-value,
    .stApp:not([data-theme="dark"]) .exam-details-value {
        color: #1d1d1f !important;
    }
    
    .stApp[data-theme="light"] .exam-details-container .exam-details-label,
    [data-theme="light"] .exam-details-container .exam-details-label,
    .stApp[data-theme="light"] .exam-details-container strong.exam-details-label,
    [data-theme="light"] .exam-details-container strong.exam-details-label,
    .stApp[data-theme="light"] .exam-details-label,
    [data-theme="light"] .exam-details-label,
    .stApp:not([data-theme="dark"]) .exam-details-container .exam-details-label,
    .stApp:not([data-theme="dark"]) .exam-details-label {
        color: #86868b !important;
    }
    
    /* Ensure all direct children and nested elements */
    .stApp[data-theme="light"] .exam-details-container > div,
    [data-theme="light"] .exam-details-container > div,
    .stApp:not([data-theme="dark"]) .exam-details-container > div {
        color: #1d1d1f !important;
    }
    
    .stApp[data-theme="light"] .exam-details-container > div > *,
    [data-theme="light"] .exam-details-container > div > *,
    .stApp:not([data-theme="dark"]) .exam-details-container > div > * {
        color: inherit !important;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    .step-container {
        animation: fadeIn 0.4s ease-out;
        padding: 1rem 1.25rem;
        margin: 0.5rem 0;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.05);
        color: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex;
        align-items: center;
    }
    
    /* Light mode step container */
    .stApp[data-theme="light"] .step-container {
        background: rgba(0, 0, 0, 0.03);
        color: #1d1d1f;
        border-color: rgba(0, 0, 0, 0.1);
    }
    
    .stApp[data-theme="light"] .step-pending {
        background: rgba(0, 0, 0, 0.03);
        color: #6e6e73;
        border-color: rgba(0, 0, 0, 0.1);
    }
    
    .step-container:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        transform: translateY(-1px);
    }
    
    .step-active {
        background: #0065BD;
        color: white;
        border-color: #0065BD;
        box-shadow: 0 4px 16px rgba(0, 101, 189, 0.4);
    }
    
    .step-completed {
        background: #0065BD;
        color: white;
        border-color: #0065BD;
        box-shadow: 0 2px 8px rgba(0, 101, 189, 0.3);
    }
    
    .step-pending {
        background: rgba(255, 255, 255, 0.05);
        color: rgba(255, 255, 255, 0.6);
        border-color: rgba(255, 255, 255, 0.1);
    }
    
    /* Status text theme adaptation */
    .status-text {
        color: rgba(255, 255, 255, 0.9);
    }
    
    .status-text-secondary {
        color: rgba(255, 255, 255, 0.6);
    }
    
    /* Light mode status text */
    .stApp[data-theme="light"] .status-text {
        color: #1d1d1f;
    }
    
    .stApp[data-theme="light"] .status-text-secondary {
        color: #6e6e73;
    }
    
    .status-icon {
        font-size: 1.25rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        margin-right: 0.75rem;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.2);
        flex-shrink: 0;
    }
    
    .status-icon svg {
        width: 16px;
        height: 16px;
    }
    
    .step-active .status-icon {
        background: rgba(255, 255, 255, 0.25);
    }
    
    .step-completed .status-icon {
        background: rgba(255, 255, 255, 0.25);
    }
    
    .step-pending .status-icon {
        background: rgba(255, 255, 255, 0.1);
    }
    
    /* Light mode status icons */
    .stApp[data-theme="light"] .status-icon {
        background: rgba(0, 0, 0, 0.08);
    }
    
    .stApp[data-theme="light"] .step-active .status-icon,
    .stApp[data-theme="light"] .step-completed .status-icon {
        background: rgba(255, 255, 255, 0.25);
    }
    
    .stApp[data-theme="light"] .step-pending .status-icon {
        background: rgba(0, 0, 0, 0.05);
    }
    
    .spinning {
        animation: spin 1s linear infinite;
    }
    
    .step-name {
        font-size: 0.9375rem;
        font-weight: 400;
        flex: 1;
        letter-spacing: -0.01em;
        color: inherit;
    }
    
    .step-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.2);
        font-size: 0.6875rem;
        font-weight: 600;
        margin-right: 0.75rem;
    }
    
    .step-pending .step-number {
        background: rgba(255, 255, 255, 0.1);
        color: rgba(255, 255, 255, 0.6);
    }
    
    /* Light mode step number */
    .stApp[data-theme="light"] .step-pending .step-number {
        background: rgba(0, 0, 0, 0.1);
        color: #6e6e73;
    }
    
    .stApp[data-theme="light"] .step-container .step-number {
        background: rgba(0, 0, 0, 0.1);
        color: #1d1d1f;
    }
</style>
<script>
(function() {
    function updateThemeColors() {
        const stApp = document.querySelector('.stApp');
        const isDark = stApp && (stApp.getAttribute('data-theme') === 'dark' || 
                                 !stApp.getAttribute('data-theme') && 
                                 window.getComputedStyle(document.body).backgroundColor === 'rgb(0, 0, 0)');
        
        const headerIntro = document.querySelector('.header-intro');
        if (headerIntro) {
            headerIntro.style.color = isDark ? 'rgba(255, 255, 255, 0.7)' : '#6e6e73';
        }
        
        const examContainers = document.querySelectorAll('.exam-details-container');
        examContainers.forEach(container => {
            if (isDark) {
                container.style.background = 'rgba(255, 255, 255, 0.08)';
                container.style.borderColor = 'rgba(255, 255, 255, 0.15)';
                container.style.color = 'rgba(255, 255, 255, 0.95)';
                // Update all child divs
                const childDivs = container.querySelectorAll('div');
                childDivs.forEach(div => {
                    div.style.color = 'rgba(255, 255, 255, 0.95)';
                });
            } else {
                container.style.background = 'rgba(0, 0, 0, 0.03)';
                container.style.borderColor = 'rgba(0, 0, 0, 0.1)';
                container.style.color = '#1d1d1f';
                // Update all child divs
                const childDivs = container.querySelectorAll('div');
                childDivs.forEach(div => {
                    div.style.color = '#1d1d1f';
                });
            }
        });
        
        const examValues = document.querySelectorAll('.exam-details-value');
        examValues.forEach(el => {
            el.style.color = isDark ? 'rgba(255, 255, 255, 0.95)' : '#1d1d1f';
        });
        
        const examLabels = document.querySelectorAll('.exam-details-label');
        examLabels.forEach(el => {
            el.style.color = isDark ? 'rgba(255, 255, 255, 0.75)' : '#86868b';
        });
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateThemeColors);
    } else {
        setTimeout(updateThemeColors, 100);
    }
    
    const observer = new MutationObserver(() => {
        setTimeout(updateThemeColors, 50);
    });
    
    if (document.querySelector('.stApp')) {
        observer.observe(document.querySelector('.stApp'), { 
            attributes: true, 
            attributeFilter: ['data-theme'] 
        });
    }
    observer.observe(document.body, { 
        attributes: true, 
        attributeFilter: ['data-theme'] 
    });
})();
</script>
""", unsafe_allow_html=True)

# Create columns for layout
left_col, right_col = st.columns([1, 1])

# Left column - file upload
with left_col:
    st.markdown("#### Upload Files")
    
    # Exam file upload
    st.markdown("**Altklausur (Exam)**")
    uploaded_file = st.file_uploader("Choose exam file", type=["pdf"], help="Upload your exam PDF file", label_visibility="collapsed", key="exam_upload")
    
    # Script file upload for RAG
    st.markdown("**Vorlesungsskript**")
    script_file = st.file_uploader("Choose script file", type=["pdf"], help="Upload lecture script PDF for question context", label_visibility="collapsed", key="script_upload")

    if uploaded_file is not None:
        st.markdown(f"<div style='font-size: 0.8125rem; color: #0065BD; margin-top: 0.5rem;'>{uploaded_file.name}</div>", unsafe_allow_html=True)
        
        if script_file is not None:
            st.markdown(f"<div style='font-size: 0.8125rem; color: #0065BD; margin-top: 0.25rem;'>{script_file.name}</div>", unsafe_allow_html=True)
        
        # Run workflow button
        st.markdown("""
        <style>
        .stButton > button {
            background-color: #0065BD !important;
            color: white !important;
            border: none !important;
            width: 100%;
        }
        .stButton > button:hover {
            background-color: #00509a !important;
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button("🚀 Run Workflow", use_container_width=True):
            st.session_state["run_workflow"] = True

        # Only proceed if button was clicked
        if st.session_state.get("run_workflow"):
            # Build the exam with dummy data only if not already built
            if st.session_state.get("uploaded_file") != uploaded_file.name:
                # Define steps with SVG icons
                steps = [
                    {"icon": "⚙", "name": "Setting up workspace"},
                    {"icon": "📄", "name": "Parsing exam questions"},
                    {"icon": "📚", "name": "Ingesting lecture script (RAG)"},
                    {"icon": "🎨", "name": "Rendering problems"},
                    {"icon": "📝", "name": "Generating exam template"},
                    {"icon": "✓", "name": "Complete!"},
                ]
                
                # Icon mapping for SVG (simple, clean icons)
                icon_svgs = {
                    "⚙": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 6v6M5.64 5.64l4.24 4.24m4.24 4.24l4.24 4.24M1 12h6m6 0h6M5.64 18.36l4.24-4.24m4.24-4.24l4.24-4.24"/></svg>',
                    "📄": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
                    "📚": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
                    "🎨": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/></svg>',
                    "📝": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
                    "✓": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>',
                    "⟳": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>',
                }
                
                # Use a mutable container to store state
                state = {"current_step": 0, "last_progress": 0}
                
                # Create placeholders in left column below upload
                st.markdown("---")
                st.markdown("#### Status")
                status_placeholder = st.empty()
                progress_placeholder = st.empty()
                step_placeholder = st.empty()
                
                def update_status(message, progress):
                    # Update progress bar using Streamlit's native progress bar
                    progress_percent = progress
                    progress_placeholder.progress(progress_percent)
                    
                    # Determine current step based on progress
                    if progress < 0.15:
                        state["current_step"] = 0
                    elif progress < 0.25:
                        state["current_step"] = 1
                    elif progress < 0.35:
                        state["current_step"] = 2
                    elif progress < 0.7:
                        state["current_step"] = 3
                    elif progress < 0.9:
                        state["current_step"] = 4
                    else:
                        state["current_step"] = 5
                    
                    current_step = state["current_step"]
                    current_step_data = message
                    
                    # Show only the current step
                    if current_step < len(steps) - 1:
                        step_class = "step-active"
                        icon_svg = icon_svgs.get("⟳", "⟳")
                        icon_class = "spinning"
                    else:
                        step_class = "step-completed"
                        icon_svg = icon_svgs.get("✓", "✓")
                        icon_class = ""
                    
                    step_html = f'<div class="step-container {step_class}"><span class="step-number">{current_step + 1}</span><span class="status-icon {icon_class}">{icon_svg}</span><span class="step-name">{current_step_data}</span></div>'
                    step_placeholder.markdown(step_html, unsafe_allow_html=True)
                    
                    # Small delay for animation effect
                    time.sleep(0.15)

                # Load and parse the exam
                exam = parse_exam_complete(uploaded_file)
                
                # Ingest lecture script for RAG if provided
                use_rag = False
                if script_file is not None:
                    try:
                        update_status("Ingesting lecture script (RAG)", 0.30)
                        
                        # Save script to temporary file
                        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                            tmp_file.write(script_file.read())
                            tmp_path = tmp_file.name
                        
                        # Ingest the script
                        ingest_script_for_rag(tmp_path)
                        use_rag = True
                        st.success(f"✅ Lecture script ingested for RAG context!")
                        os.unlink(tmp_path)
                    except Exception as e:
                        st.warning(f"⚠️ Could not ingest script: {e}")
                        use_rag = False
                

                exam_path, solution_path = build_exam(exam, status_callback=update_status)
                print(f"Exam built at: {exam_path}")
                print(f"Solution built at: {solution_path}")

                st.session_state['exam_path'] = exam_path
                st.session_state['solution_path'] = solution_path
                st.session_state['parsed_exam'] = exam
                
                # Final update: show completed step
                progress_placeholder.progress(1.0)
                
                # Show final step as completed
                final_step = steps[-1]
                check_icon = icon_svgs.get("✓", "✓")
                final_step_html = f'<div class="step-container step-completed"><span class="step-number">{len(steps)}</span><span class="status-icon">{check_icon}</span><span class="step-name">{final_step["name"]}</span></div>'
                step_placeholder.markdown(final_step_html, unsafe_allow_html=True)
                
                
                st.session_state["uploaded_file"] = uploaded_file.name
                st.session_state["exam_built"] = True
                st.session_state["use_rag"] = use_rag
            # st.session_state["use_rag"] = use_rag


with right_col:
    if 'exam_path' in st.session_state and 'solution_path' in st.session_state:
        st.markdown("#### Exam Built Successfully!")
        
        # Read the exam file
        with open(st.session_state['exam_path'], 'rb') as exam_file:
            exam_bytes = exam_file.read()
        
        # Read the solution file
        with open(st.session_state['solution_path'], 'rb') as solution_file:
            solution_bytes = solution_file.read()
        
        # Create download buttons
        st.download_button(
            label="📄 Download Exam",
            data=exam_bytes,
            file_name="exam.pdf",
            mime="application/pdf"
        )
        
        st.download_button(
            label="📝 Download Solution",
            data=solution_bytes,
            file_name="solution.pdf",
            mime="application/pdf"
        )
        

# # Right column - Exam Details (will be populated when exam is built)
# with right_col:
#     if uploaded_file is None or not st.session_state.get("exam_built"):
#         st.markdown("#### Exam Details")
#         st.markdown("<div class='status-text-secondary' style='font-size: 0.8125rem; margin-top: 0.5rem;'>Exam details will appear here after processing</div>", unsafe_allow_html=True)
#     else:
#         # Display exam details on the right side
#         st.markdown("#### Exam Details")
        
#         # Show exam summary
#         if "exam_summary" not in st.session_state:
#             exam = get_dummy_exam()
#             st.session_state["exam_summary"] = {
#                 "title": exam.exam_title,
#                 "module": exam.module,
#                 "total_points": exam.total_points,
#                 "total_time": exam.total_time_min,
#                 "num_problems": len(exam.exam_content.problems)
#             }
        
#         summary = st.session_state["exam_summary"]
#         st.markdown(f"""
#         <div class="exam-details-container" style="padding: 1rem; border-radius: 12px; margin-top: 1rem; background: rgba(0, 0, 0, 0.03); border: 1px solid rgba(0, 0, 0, 0.1); color: #1d1d1f;">
#             <div style="margin-bottom: 0.75rem; font-size: 0.875rem; color: #1d1d1f;">
#                 <strong class="exam-details-label" style="display: block; margin-bottom: 0.25rem; color: #86868b;">Title</strong>
#                 <span class="exam-details-value" style="color: #1d1d1f;">{summary['title']}</span>
#             </div>
#             <div style="margin-bottom: 0.75rem; font-size: 0.875rem; color: #1d1d1f;">
#                 <strong class="exam-details-label" style="display: block; margin-bottom: 0.25rem; color: #86868b;">Module</strong>
#                 <span class="exam-details-value" style="color: #1d1d1f;">{summary['module']}</span>
#             </div>
#             <div style="margin-bottom: 0.75rem; font-size: 0.875rem; color: #1d1d1f;">
#                 <strong class="exam-details-label" style="display: block; margin-bottom: 0.25rem; color: #86868b;">Total Points</strong>
#                 <span class="exam-details-value" style="color: #1d1d1f;">{summary['total_points']}</span>
#             </div>
#             <div style="margin-bottom: 0.75rem; font-size: 0.875rem; color: #1d1d1f;">
#                 <strong class="exam-details-label" style="display: block; margin-bottom: 0.25rem; color: #86868b;">Duration</strong>
#                 <span class="exam-details-value" style="color: #1d1d1f;">{summary['total_time']} minutes</span>
#             </div>
#             <div style="font-size: 0.875rem; color: #1d1d1f;">
#                 <strong class="exam-details-label" style="display: block; margin-bottom: 0.25rem; color: #86868b;">Problems</strong>
#                 <span class="exam-details-value" style="color: #1d1d1f;">{summary['num_problems']}</span>
#             </div>
#         </div>
#         """, unsafe_allow_html=True)
