import os
import random
from fpdf import FPDF
from datetime import datetime

# Skills and experience pools
PROGRAMMING_LANGUAGES = [
    "Python", "Java", "C#", "JavaScript", "TypeScript", "Go", "Rust", "Ruby", "C++", "Scala",
    "PHP", "Swift", "Kotlin", "R", "MATLAB"
]

FRAMEWORKS = [
    "React", "Angular", "Vue.js", "Django", "Flask", "Spring Boot", "ASP.NET Core", "Express.js",
    "FastAPI", "Laravel", "Ruby on Rails", "Hibernate", "TensorFlow", "PyTorch", "Node.js"
]

CLOUD_TECHNOLOGIES = [
    "Azure", "AWS", "GCP", "Kubernetes", "Docker", "Terraform", "OpenShift", "Cloud Foundry",
    "Azure DevOps", "AWS ECS", "Cloud Formation", "Ansible", "Prometheus", "Grafana"
]

DATABASES = [
    "MongoDB", "PostgreSQL", "MySQL", "Redis", "Cassandra", "DynamoDB", "CosmosDB", 
    "Elasticsearch", "Neo4j", "Oracle", "SQL Server", "InfluxDB"
]

CERTIFICATIONS = [
    "Certified Cloud Architect", "Certified Kubernetes Administrator", 
    "Certified Information Systems Security Professional (CISSP)",
    "Project Management Professional (PMP)", "AWS Solutions Architect",
    "Azure Solutions Architect", "Google Cloud Professional Architect",
    "Certified Scrum Master", "Certified DevOps Engineer",
    "Certified Data Scientist", "Certified ML Engineer",
    "CompTIA Security+", "ITIL Foundation", "Red Hat Certified Engineer"
]

COMPANIES = [
    ("Contoso", "Enterprise Software"),
    ("Northwind Traders", "E-commerce"),
    ("Adventure Works", "Manufacturing Software"),
    ("Woodgrove Bank", "Financial Technology"),
    ("Alpine Ski House", "Digital Solutions"),
    ("Fourth Coffee", "Cloud Services"),
    ("Graphic Design Institute", "Creative Technology"),
    ("Tailspin Toys", "Software Solutions"),
    ("Wide World Importers", "Technology Consulting"),
    ("Fabrikam", "Digital Innovation")
]

CONTOSO_JOB_TEMPLATE = """
{role_title}
Contoso Corporation

Location: {location}

About Contoso:
At Contoso, we believe in transforming businesses through innovative cloud solutions and cutting-edge technology. Our mission is to revolutionize enterprise software and empower organizations worldwide.

Role Overview:
{overview}

Key Responsibilities:
{responsibilities}

Qualifications:
{qualifications}

Additional Requirements:
{additional}

Contoso is committed to creating a diverse environment and is proud to be an equal opportunity employer. All qualified applicants will receive consideration for employment without regard to race, color, religion, gender, gender identity or expression, sexual orientation, national origin, genetics, disability, age, or veteran status.
"""

RESUME_TEMPLATE = """
{name}
{email} | {phone} | {location}

PROFESSIONAL SUMMARY
{summary}

WORK EXPERIENCE
{experience}

EDUCATION
{education}

SKILLS
{skills}

CERTIFICATIONS
{certifications}
"""

def generate_experience(years_of_experience):
    """Generate random work experience with realistic progression"""
    experience = []
    current_year = datetime.now().year
    current_date = current_year
    
    companies_used = random.sample(COMPANIES, min(len(COMPANIES), years_of_experience // 2))
    for company, industry in companies_used:
        duration = random.randint(1, 3)
        start_year = current_date - duration
        
        # Generate random achievements
        achievements = [
            "Led development of cloud-native applications",
            "Implemented microservices architecture",
            "Reduced system latency by 40%",
            "Managed team of 5-8 engineers",
            "Architected scalable solutions",
            "Improved deployment efficiency",
            "Developed CI/CD pipelines",
            "Optimized database performance",
            "Led agile transformation",
            "Reduced operational costs"
        ]
        
        experience.append(f"""
{company} ({industry})
{random.choice(['Senior', 'Lead', 'Principal', 'Staff'])} Engineer | {start_year} - {current_date if company == companies_used[-1][0] else start_year + duration}
• {random.choice(achievements)}
• {random.choice(achievements)}""")
        
        current_date = start_year

    return "\n".join(reversed(experience))

def generate_skills():
    """Generate a random but coherent set of skills"""
    skills = []
    # Pick random skills from each category
    skills.extend(random.sample(PROGRAMMING_LANGUAGES, random.randint(3, 5)))
    skills.extend(random.sample(FRAMEWORKS, random.randint(2, 4)))
    skills.extend(random.sample(CLOUD_TECHNOLOGIES, random.randint(3, 5)))
    skills.extend(random.sample(DATABASES, random.randint(2, 3)))
    
    # Group skills by category
    return f"""
Programming: {', '.join(random.sample(PROGRAMMING_LANGUAGES, 4))}
Frameworks: {', '.join(random.sample(FRAMEWORKS, 3))}
Cloud & DevOps: {', '.join(random.sample(CLOUD_TECHNOLOGIES, 4))}
Databases: {', '.join(random.sample(DATABASES, 2))}"""

def generate_certifications():
    """Generate a realistic set of certifications"""
    return "\n• ".join(random.sample(CERTIFICATIONS, random.randint(2, 4)))

def create_job_posting(output_path="job_description.pdf"):
    """Create a Contoso-style job posting PDF"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    job_content = CONTOSO_JOB_TEMPLATE.format(
        role_title="Senior Cloud Solutions Engineer",
        location="Bellevue, WA",
        overview="""We are seeking a Senior Cloud Solutions Engineer to join our Enterprise Cloud Division. 
        You will be instrumental in architecting and delivering next-generation cloud solutions that power Contoso's enterprise customers.""",
        responsibilities="""
• Design and implement enterprise-grade cloud solutions
• Lead technical architecture decisions for major client implementations
• Drive innovation in our cloud service offerings
• Mentor team members and promote best practices""",
        qualifications="""
• 5+ years of experience in cloud architecture and development
• Strong background in distributed systems and microservices
• Experience with major cloud platforms (Azure/AWS/GCP)
• Track record of delivering complex technical solutions""",
        additional="""
• Experience with agile methodologies
• Strong communication and presentation skills
• Background in enterprise software development"""
    )
    
    pdf.multi_cell(0, 10, txt=job_content)
    pdf.output(output_path)

def create_resume(name, role, output_path):
    """Create a resume PDF with randomized experience and skills"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    years_of_experience = random.randint(5, 15)
    
    resume_content = RESUME_TEMPLATE.format(
        name=name,
        email=f"{name.lower().replace(' ', '.')}@email.com",
        phone="(555) 123-4567",
        location=random.choice(["Seattle, WA", "Bellevue, WA", "Redmond, WA", "San Francisco, CA"]),
        summary=f"""Experienced {role} with {years_of_experience}+ years in enterprise software development. 
        Specialized in cloud architecture and distributed systems.""",
        experience=generate_experience(years_of_experience),
        education="""
Master of Science in Computer Science
University of Washington | 2016

Bachelor of Science in Software Engineering
Georgia Institute of Technology | 2014""",
        skills=generate_skills(),
        certifications=generate_certifications()
    )
    
    pdf.multi_cell(0, 10, txt=resume_content)
    pdf.output(output_path)

def main():
    """Create job posting and resume files if they don't exist"""
    # Create resumes directory if it doesn't exist
    os.makedirs("resumes", exist_ok=True)
    
    # Create job posting if it doesn't exist
    if not os.path.exists("job_description.pdf"):
        create_job_posting()
        print("Created job description PDF")
    
    # Get list of resume names from main.py
    from main import RESUME_NAMES
    
    # Create resumes if they don't exist
    for resume_name in RESUME_NAMES:
        resume_path = os.path.join("resumes", resume_name)
        if not os.path.exists(resume_path):
            # Extract name from filename (e.g., "Resume_DevOps_Engineer_Alexander_Kumar.pdf" -> "Alexander Kumar")
            name = " ".join(resume_name.split("_")[3:-1])
            create_resume(name, "Software Engineer", resume_path)
            print(f"Created resume for {name}")

if __name__ == "__main__":
    main()
