# User Stories & Use Cases (v0.1)

> **Purpose**: Define key user personas and their primary workflows to guide feature prioritization and UX design.

---

## 1. Primary Persona

**Alex** - Home cooking enthusiast
- Saves 10-20 recipes per month from various sources
- Wants to adapt recipes to dietary preferences
- Values organization and quick retrieval
- Not interested in social features for MVP

## 2. Core User Stories

### 2.1 Recipe Creation from Text

**As a** home cook  
**I want to** paste messy recipe text and get a clean structured recipe  
**So that** I can quickly add recipes I find online without manual formatting

**Acceptance Criteria:**
- Can paste HTML/text from any website into chat
- AI extracts recipe from messy content
- Structured recipe appears in live preview
- Can refine extraction via chat

### 2.2 Recipe Refinement

**As a** home cook  
**I want to** modify recipes through natural conversation  
**So that** I can adapt them to my preferences and constraints

**Acceptance Criteria:**
- Can ask for ingredient substitutions
- Can request scaling (e.g., "make this for 2 people")
- Can simplify complex instructions
- Changes appear live in the recipe preview

### 2.3 Recipe Generation

**As a** home cook  
**I want to** ask for recipes based on my needs  
**So that** I can get custom recipe ideas without searching

**Acceptance Criteria:**
- Can describe dietary needs or constraints
- Can specify meal type and occasion
- AI generates appropriate recipe
- Recipe appears structured and ready to cook

### 2.4 Recipe Browsing

**As a** home cook  
**I want to** browse my recipe collection easily  
**So that** I can find what to cook

**Acceptance Criteria:**
- See all recipes in chronological order
- Can quickly scan recipe titles and descriptions
- Recent recipes appear at the top
- Fast loading of recipe list

## 3. Detailed Use Cases

### UC1: Extract Recipe from Text

**Primary Flow:**
1. User opens chat interface
2. User pastes recipe text/HTML and says "extract this recipe"
3. AI analyzes text and responds with structured recipe
4. Recipe appears in live preview
5. User can refine via chat or save as-is

**Alternative Flows:**
- 3a. If text unclear, AI asks clarifying questions
- 4a. User can directly edit fields in preview
- 5a. User can continue chatting to refine recipe

### UC2: Refine Recipe via Chat

**Primary Flow:**
1. User opens recipe in editor
2. User types request in chat (e.g., "make this vegan")
3. System suggests modifications
4. User sees changes in live preview
5. User accepts or modifies suggestions
6. System saves new version

**Alternative Flows:**
- 3a. If unclear request, system asks clarification
- 4a. User can directly edit fields instead
- 6a. User can revert to previous version

### UC3: Generate Recipe from Description

**Primary Flow:**
1. User opens chat interface
2. User describes what they want: "lunch for my son, no refrigeration needed"
3. AI generates appropriate recipe based on constraints
4. Recipe appears in live preview
5. User can refine or save

**Alternative Flows:**
- 3a. If request unclear, AI asks for more details
- 4a. User requests modifications via chat
- 5a. User can generate alternatives

## 4. Non-Functional Use Cases

### UC4: Quick Recipe Access

**Requirement:** Load any recipe in <200ms
**Flow:**
1. User clicks recipe from list
2. System retrieves from cache/DB
3. Recipe displays immediately

### UC5: Reliable Text Extraction

**Requirement:** 95%+ success rate for extracting recipes from common text formats
**Flow:**
1. User pastes text containing recipe
2. AI extracts structured recipe data
3. Recipe requires minimal manual cleanup

## 5. Future Use Cases (Post-MVP)

- Import from files (PDF, images, videos)
- Search and filtering recipes
- Recipe versioning and history
- Export to various formats
- Share recipe with family member
- Generate shopping list from recipes
- Plan weekly meals
- Get nutrition information
- Voice-guided cooking mode

---

*End of User Stories v0.1*