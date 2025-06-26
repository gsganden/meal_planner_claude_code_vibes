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

### UC0.0: User Authentication

**UC0.0.1: New User Account Creation (Sign Up)**

**Primary Flow:**
1. User visits app URL in browser for first time
2. Sees login page with "Sign In" form displayed by default
3. User clicks "Don't have an account? Sign up" link
4. Form switches to "Sign Up" mode with email, password, and confirm password fields
5. User enters valid email address (e.g., "newuser@example.com")
6. User enters password meeting requirements (min 8 characters)
7. User enters matching confirmation password
8. User clicks "Create Account" button
9. System validates inputs and creates new account
10. User immediately signed in and redirected to empty recipe list page
11. User sees "Create Your First Recipe" message and can begin using app

**Alternative Flows:**
- 5a. User enters invalid email format → sees "Please enter a valid email address" error below field
- 6a. User enters weak password → sees "Password must be at least 8 characters" error below field
- 7a. Confirmation password doesn't match → sees "Passwords do not match" error below field
- 8a. Email already exists → sees "An account with this email already exists. Try signing in instead."
- 9a. Network error during signup → sees "Unable to create account. Please try again." with retry option

**UC0.0.2: Existing User Authentication (Sign In)**

**Primary Flow:**
1. User visits app URL in browser
2. Sees login page with "Sign In" form (email and password fields)
3. User enters their registered email address
4. User enters their password
5. User clicks "Sign In" button
6. System validates credentials against stored account
7. User immediately redirected to recipe list with their existing recipes
8. User can continue working with saved recipes

**Alternative Flows:**
- 4a. User enters wrong password → sees "Invalid email or password" error message
- 4b. User enters unregistered email → sees "Invalid email or password" error message (no email enumeration)
- 5a. User clicks "Don't have an account? Sign up" → switches to sign-up form (UC0.0.1)
- 6a. Network error during sign-in → sees "Unable to sign in. Please check your connection." with retry option

**UC0.0.3: Form Mode Switching**

**Primary Flow:**
1. User on login page sees "Sign In" form by default
2. User clicks "Don't have an account? Sign up" link
3. Form smoothly transitions to "Sign Up" mode showing additional confirm password field
4. Page title changes to "Create Account" and button text changes to "Create Account"
5. User can switch back by clicking "Already have an account? Sign in" link
6. Form returns to "Sign In" mode with just email and password fields

**UC0.0.4: Input Validation and Error Handling**

**Primary Flow:**
1. User begins filling out authentication form (either sign-in or sign-up)
2. User sees real-time validation feedback as they type
3. Email field validates format on blur
4. Password field shows strength indicator for sign-up
5. Confirm password field validates match in real-time for sign-up
6. Submit button remains disabled until all validations pass
7. User sees clear, specific error messages for any validation failures

**Password Requirements:**
- Minimum 8 characters
- At least one letter and one number
- No maximum length restriction

**UC0.0.5: Session Management**

**Primary Flow:**
1. User successfully signs in and sees recipe list
2. User refreshes browser page → stays signed in, remains on recipe list
3. User closes browser and reopens app later → stays signed in if within session duration
4. User can click "Sign Out" button in app header to explicitly log out
5. Sign out redirects to login page and clears stored session

**Alternative Flows:**
- 3a. Session has expired → user automatically redirected to login page with message "Your session has expired. Please sign in again."
- 4a. User signs out → sees login page with confirmation "You have been signed out successfully."

**UC0.0.6: Form Validation and User Feedback**

**Primary Flow:**
1. User begins filling out authentication form (signup or signin mode)
2. Email field validates format automatically on blur (shows red border if invalid)
3. In signup mode: password field shows requirements help text below input
4. In signup mode: confirm password field shows "Passwords do not match" in real-time if different from password
5. Submit button remains disabled (gray) until all validations pass
6. Submit button becomes enabled (blue) when form is valid and ready to submit

**Alternative Flows:**
- 3a. User types weak password in signup → sees "Password must be at least 8 characters with at least one letter and one number" help text
- 4a. User switches from signup to signin mode → password and confirm password fields clear, email field retains value, error messages clear
- 4b. User switches from signin to signup mode → password field clears, form shows additional confirm password field

**UC0.0.7: Loading States and Application Initialization**

**Primary Flow:**
1. User visits app URL → sees loading spinner with "Loading..." text while checking existing session
2. If valid session exists → automatic redirect to recipe list (no login page shown)
3. If no valid session → login page appears in signin mode
4. User submits authentication form → button text changes to "Signing in..." or "Creating Account..." with disabled state
5. On successful authentication → immediate transition to recipe list without page navigation

**Alternative Flows:**
- 2a. Session expired during app startup → login page appears with message "Your session has expired. Please sign in again."
- 4a. Authentication request fails → button returns to normal state, error message appears above form
- 5a. Network error during authentication → button returns to normal state, shows "Unable to connect" error

**UC0.0.8: Logout and Session Termination**

**Primary Flow:**
1. User is signed in and viewing recipe list
2. User clicks "Sign Out" button in app header
3. User immediately redirected to login page in signin mode
4. All stored session data cleared from browser
5. User cannot access protected pages without signing in again

**Alternative Flows:**
- 2a. Network error during logout → user still redirected to login page, session cleared locally
- 3a. User sees login page with success message "You have been signed out successfully" (optional)

**UC0.0.9: Error Message Behavior and Recovery**

**Primary Flow:**
1. User encounters authentication error (wrong password, network failure, etc.)
2. Error message appears immediately above the form with red background
3. Error message remains visible until user takes corrective action
4. User modifies form input or switches modes → error message disappears
5. User can retry authentication with corrected information

**Error Message Content:**
- Invalid credentials: "Invalid email or password"
- Duplicate signup: "An account with this email already exists. Try signing in instead."
- Network error: "Unable to connect. Please check your connection and try again."
- Weak password: "Password must be at least 8 characters with at least one letter and one number"
- Password mismatch: "Passwords do not match"

**Alternative Flows:**
- 3a. User switches between signin/signup modes → error message clears automatically
- 4a. Multiple rapid authentication attempts → shows rate limiting message "Too many attempts. Please wait before trying again."

**UC0.0.10: Password Reset Flow**

**Primary Flow:**
1. User on signin page clicks "Forgot your password?" link below login form
2. Form switches to password reset mode showing email input field
3. User enters their registered email address
4. User clicks "Send Reset Link" button
5. System displays message: "If an account exists with this email, you'll receive password reset instructions"
6. User checks email and clicks reset link in email
7. User redirected to reset password page with token pre-filled
8. User enters new password and confirms it
9. User clicks "Reset Password" and sees success message: "Password updated successfully"
10. User automatically redirected to signin page

**Alternative Flows:**
- 4a. User enters unregistered email → same success message shown (no email enumeration)
- 6a. User doesn't receive email → can retry with "Didn't receive email? Try again" link
- 7a. Reset token expired → user sees "This reset link has expired. Please request a new one."
- 8a. New password doesn't meet requirements → shows validation errors in real-time
- 9a. Network error during reset → shows "Unable to reset password. Please try again."

### UC0: Application Entry & Navigation (Post-Authentication)

> **Note**: These flows assume user has completed authentication per UC0.0 above.

**Primary Flow - New User (First Recipe):**
1. User successfully signed up and sees empty recipe list with "Create Your First Recipe" message
2. User clicks "New Recipe" button or "Create Your First Recipe" button  
3. System shows brief loading state while creating recipe on server
4. Server creates recipe with UUID and title "Untitled Recipe 1", then redirects to `/recipe/{id}`
5. User lands in recipe editor with auto-generated title, empty ingredients/steps arrays, and chat prompt: "How can I help you create a recipe?"
6. User proceeds with recipe creation via chat or direct form editing, with autosave active from the start

**Primary Flow - Returning User (Existing Recipes):**
1. User successfully signed in and sees recipe list in reverse chronological order (newest first)
2. User scrolls through recipes, seeing titles, descriptions, and last updated dates
3. User clicks recipe title to open in editor
4. User lands in editor with structured form populated, chat starts fresh

**Alternative Flows:**
- 1a. User clicks "New Recipe" to create fresh recipe instead of editing existing
- 3a. User uses back button/navigation to return to recipe list from editor  
- 3b. User sees "Connection lost" banner if network fails, with retry option

### UC1: Extract Recipe from Text

**Primary Flow:**
1. User is in recipe editor (from UC0 - either new recipe or existing)
2. User pastes recipe text/HTML into chat (no specific command needed)
3. AI automatically detects recipe content and responds: "I found a recipe for Chocolate Chip Cookies! Let me structure it for you."
4. User sees structured form fields populate in real-time: title fills in, ingredients appear as separate lines, steps populate as numbered items
5. User can refine via chat ("make serving size bigger") or directly edit form fields

**Alternative Flows:**
- 3a. **Ambiguous content**: AI responds "I see some recipe-like content. Should I try to extract a recipe from this?"
- 3b. **Recipe + other text**: AI automatically extracts just the recipe part: "I found a pasta recipe in this text. Here it is structured for you."
- 3c. **No recipe detected**: AI responds "I don't see recipe content here. Would you like me to help you create a recipe instead?"
- 4a. User can directly edit any form field (title, ingredient lines, steps) while AI is responding
- 4b. Direct form edits send system message to chat: "User updated [field]: [old] → [new]"
- 5a. User clicks "Save Recipe" for explicit save or relies on 2-second autosave

### UC2: Refine Recipe via Chat

**Primary Flow:**
1. User opens existing recipe in editor (structured form populated, chat starts fresh)
2. User types request in chat (e.g., "make this vegan")
3. AI responds: "I'll modify the ingredients to make this vegan..." and updates form fields in real-time
4. User sees ingredient lines change (e.g., "milk" → "oat milk"), steps updated as needed
5. User can continue refining or click "Save Recipe" (autosave happens automatically after 2 seconds)

**Alternative Flows:**
- 3a. If unclear request, AI asks clarification: "What type of vegan substitute would you prefer for the cheese?"
- 4a. User can directly edit any form field instead of using chat
- 4b. Direct edits send system message: "User changed ingredient 3: 'cheddar cheese' → 'nutritional yeast'"
- 5a. User sees "Saving..." indicator during autosave, "Saved" when complete

### UC3: Generate Recipe from Description

**Primary Flow:**
1. User is in new recipe editor (empty structured form visible)
2. User describes what they want: "lunch for my son, no refrigeration needed"
3. AI responds: "Perfect! I'll create a portable lunch recipe for you." and begins populating form fields
4. User sees title appear ("No-Refrigeration Turkey Wraps"), ingredients populate line by line, steps fill in sequentially
5. User can refine via chat ("add more protein") or directly edit form fields

**Alternative Flows:**
- 3a. If request unclear, AI asks for more details: "What type of foods does your son enjoy? Any allergies to consider?"
- 4a. User requests modifications via chat during generation: "make it vegetarian instead"
- 4b. User directly edits form fields while AI is generating
- 5a. User can ask for alternatives: "show me a different lunch option"

### UC3.5: Manual Recipe Building

**Primary Flow:**
1. User clicks "New Recipe" and lands in editor with "Untitled Recipe {N}" auto-generated title
2. User immediately starts typing new title: "Mom's Chocolate Chip Cookies"
3. User sees yellow border indicating unsaved changes, then autosave after 2 seconds
4. User clicks "Add Ingredient" and types "2 cups flour"
5. User continues adding ingredients and steps manually without using chat
6. Each field edit triggers autosave, building recipe incrementally

**Alternative Flows:**
- 2a. User keeps auto-generated title and proceeds to add ingredients/steps
- 4a. User copies/pastes ingredient list from external source
- 5a. User decides to ask chat for help: "suggest baking time and temperature"
- 6a. User switches between manual editing and chat assistance seamlessly

### UC4: Direct Field Editing with Chat Sync

**Primary Flow:**
1. User has recipe open in editor (existing recipe or one being created via chat)
2. User directly clicks and edits a form field (e.g., changes title from "Pasta Salad" to "Mediterranean Pasta Salad")
3. User sees yellow border on field indicating unsaved changes
4. System sends message to chat: "User updated title: 'Pasta Salad' → 'Mediterranean Pasta Salad'"
5. After 2 seconds, autosave occurs and user sees "Saving..." then "Saved" indicator

**Alternative Flows:**
- 2a. User edits ingredient line, adding or removing items from the list
- 2b. User edits step text or reorders steps
- 2c. User makes multiple rapid edits - system debounces and only shows final state in chat
- 3a. User clicks "Save Recipe" for immediate save instead of waiting for autosave
- 5a. Save fails due to network issue - user sees error message with retry option

## 5. Non-Functional Use Cases

### UC5: Quick Recipe Access

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