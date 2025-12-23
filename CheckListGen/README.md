# CheckListGen - Solana Anchor Security Audit Tool

## Overview

CheckListGen is a Python script designed to analyze Solana Anchor Rust programs for security auditing purposes. It provides two main functionalities:

1. **Account Usage Checklist**: Generates a comprehensive checklist of all accounts in your Solana Anchor program, showing which instructions/contexts use them and what attributes they have (mutable, signer, init, constraints, etc.)

2. **Template-Based Code Pattern Matching**: Scans code against customizable security templates to identify potential security issues like unchecked math operations, unchecked accounts, and more.

## Features

### 1. Account Usage Analysis
The script parses Anchor Rust files to extract:
- All account definitions in `#[derive(Accounts)]` contexts
- Account types (Signer, Account, Program, etc.)
- Which instructions/contexts use each account
- Account attributes in each context:
  - 🔄 **MUTABLE** - Account can be modified
  - ✍️ **SIGNER** - Account must sign the transaction
  - 🆕 **INIT** - Account will be initialized
  - ⚠️ **CONSTRAINT** - Custom constraints applied
  - Other custom attributes

### 2. Security Template Checks
The script uses JSON templates to identify potential security issues:
- Math operator usage (overflow/underflow risks)
- UncheckedAccount usage
- Exact equality checks
- Custom patterns you define

## Usage

```bash
python3 checkListGen.py <project_dir> <rules_dir> [--ignore-dirs <dirs>]
```

### Arguments:
- `project_dir`: Path to your Solana Anchor project directory
- `rules_dir`: Path to the directory containing JSON rule templates
- `--ignore-dirs`: (Optional) Comma-separated list of directories to ignore

### Example:
```bash
python3 checkListGen.py ./my-anchor-project ./templates --ignore-dirs "node_modules,target"
```

### Installation
Please install using a virtual environment.
```bash
python3 -m venv venv
source venv/bin/activate
```

## Output

The script generates a `checkList.md` file containing:

1. **Rust Files Found**: List of all .rs files with `#[derive(Accounts)]`
2. **Context Structures**: Detailed breakdown of each Account context
3. **Account Usage Checklist**: Comprehensive account usage matrix
4. **Rule Check Results**: Code snippets matching security templates

***
## Example Output

```markdown
## 📋 ACCOUNT USAGE CHECKLIST

### 🔑 Account: `authority`
**Type:** `Signer<'info>`
**Used in 3 instruction(s)/context(s):**

- **Context/Instruction: `Initialize`**
  - File: `example_test/test_program.rs`
  - **Attributes:**
    - 🔄 **MUTABLE** (mut)

- **Context/Instruction: `Update`**
  - File: `example_test/test_program.rs`
  - **Attributes:** None specified
```

## Rule checks returned the list of code to check below:
### File: /example/programs/example/src/lib.rs
   #: Match found on : UncheckedAccount<
   #: Found an UncheckedAccount account type check for security safety

```
23-        /// CHECK: User profile account
24:        pub user_profile: UncheckedAccount<'info>,
25-        pub authority: Signer<'info>,

```
### File: /example/programs/example/src/lib.rs
   #: Match found on : +
   #: Found math operator check code for over/underflows

```
73-
74:        profile.nft_count += 1;
75-       

```
### File: /example/programs/example/src/lib.rs
   #: Match found on : ==
   #: Found an exact equivalency check

```
69-        require!(
70:            profile.authority == ctx.accounts.authority.key(),
71-           ExampleError::Unauthorized

```
*end of example output*
***
## Template Files

Templates are JSON files in the `templates/` directory:

### Example Template (mathOperators.json):
```json
{
  "name": "MathOperators",
  "match": ["+", "- ", "* ", " - ", " * ", "/"],
  "description": "Found math operator check code for over/underflows"
}
```

### Available Templates:
- `mathOperators.json` - Detects arithmetic operations
- `UncheckedAccount.json` - Finds UncheckedAccount usage
- `exactlyEqual.json` - Identifies exact equality checks
- `incorrectExponent.json` - Checks for exponent issues
- `ExternalInvoke.json` - Finds external invocations

## Creating Custom Templates

Create a new JSON file in the `templates/` directory:

```json
{
  "name": "YourCheckName",
  "match": ["pattern1", "pattern2"],
  "description": "Description of what this check finds"
}
```

## Use Cases

### Security Auditing
- Identify accounts that are mutable without constraints
- Find accounts used across multiple contexts
- Verify signer requirements
- Check for proper initialization

### Code Review
- Generate comprehensive account usage documentation
- Track account attribute changes across contexts
- Identify potential security vulnerabilities

### Compliance
- Document all account interactions
- Track mutable state changes
- Verify constraint usage

## Disclaimer

**I DO NOT WARRANTY THIS CODE TO BE BUG FREE OR TO BE FIT FOR PURPOSE. RUNNING checkListGen AGAINST A PROJECT DOES NOT GUARANTEE THAT THE PROJECT IS SECURE AND/OR BUG FREE.**

This tool is meant to assist in security auditing but should not be the only method used. Always conduct thorough manual reviews and testing.

## Requirements

- Python 3.6+
- Standard library only (no external dependencies)

## License

Use at your own risk. No warranty provided.

## Example Test

Run the included test:
```bash
python3 checkListGen.py example_test templates
```

This will analyze the example Anchor program in `example_test/test_program.rs` and generate a report showing:
- Account usage across Initialize, Update, and Transfer contexts
- Potential math overflow issues
- Constraint usage patterns
