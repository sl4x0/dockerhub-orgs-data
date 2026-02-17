# Contributing to dockerhub-orgs-data

Thank you for your interest in contributing to dockerhub-orgs-data! This guide will help you understand how to contribute effectively.

## What We're Looking For

We appreciate contributions in the following areas:

1. **DockerHub Organizations/Usernames** - Adding or updating DockerHub organization mappings
2. **Bug Bounty Programs** - Adding new bug bounty or vulnerability disclosure programs
3. **Corrections** - Fixing incorrect or outdated information
4. **Scripts** - Improving or adding new utility scripts
5. **Documentation** - Enhancing README or this contributing guide

## How to Contribute

### Adding DockerHub Organizations

1. **Fork the repository** and clone it locally
2. **Choose a program** from the TODO list:

   ```bash
   ./scripts/todo.sh
   ```

3. **Research the DockerHub organization**:
   - Search on DockerHub: https://hub.docker.com/search?q=COMPANY_NAME
   - Check company documentation and GitHub repositories
   - Look for Dockerfile references in their public repos
   - Verify the organization exists and is official

4. **Update the TSV file**:
   - Open the appropriate file in `dockerhub-orgs-data/` directory
   - Replace `?` with the DockerHub URL (e.g., `https://hub.docker.com/u/docker`)
   - If no organization exists after thorough research, replace `?` with `-`
   - Ensure proper tab separation (TSV format)

5. **Verify your changes**:

   ```bash
   ./scripts/all-dockerhub-orgs.sh
   ```

6. **Commit and push**:

   ```bash
   git add .
   git commit -m "Add DockerHub org for COMPANY_NAME"
   git push origin main
   ```

7. **Create a Pull Request** with a clear description

### Adding New Bug Bounty Programs

1. **Determine the platform** (HackerOne, Bugcrowd, Intigriti, YesWeHack, etc.)
2. **Edit or create the appropriate TSV file** in `dockerhub-orgs-data/`
3. **Add a new line** with the format:

   ```
   <bug_bounty_program_url>	?
   ```

   Replace the space with an actual TAB character

4. **If you know the DockerHub organization**, add it directly:
   ```
   https://hackerone.com/example	https://hub.docker.com/u/example
   ```

### File Format Guidelines

- **Use TSV format**: Tab-separated values, not spaces
- **Keep it sorted**: Maintain alphabetical order when possible
- **Verify URLs**: Ensure all URLs are valid and accessible
- **Be consistent**: Follow existing patterns in the files

### Validation Checklist

Before submitting a pull request, ensure:

- [ ] DockerHub organization URL is correct and accessible
- [ ] File uses proper TAB separation (not spaces)
- [ ] No trailing whitespace
- [ ] Changes are committed with a clear message
- [ ] You've tested the scripts still work

### Commit Message Guidelines

Use clear, descriptive commit messages:

- ✅ `Add DockerHub org for GitHub`
- ✅ `Update Netflix DockerHub username`
- ✅ `Add HackerOne programs from XYZ source`
- ✅ `Mark Shopify as having no DockerHub presence`
- ❌ `Update file`
- ❌ `Changes`

### Quality Standards

1. **Verify the organization is official**: Don't add unofficial or personal accounts
2. **Document your sources**: If adding multiple orgs, mention how you found them
3. **Test your changes**: Run the scripts to ensure nothing breaks
4. **Be thorough**: Don't mark something as `-` without proper research

## Research Tips

### Finding DockerHub Organizations

1. **Direct search on DockerHub**:

   ```
   https://hub.docker.com/search?q=COMPANY
   ```

2. **Check GitHub repositories**:
   - Look for Dockerfiles
   - Search for "FROM" statements in Dockerfiles
   - Check CI/CD configurations

3. **Company documentation**:
   - Official installation guides
   - Developer documentation
   - Blog posts about Docker/containers

4. **Search engines**:

   ```
   site:hub.docker.com COMPANY_NAME
   "hub.docker.com/u" COMPANY_NAME
   ```

5. **API verification**:
   ```bash
   curl -s "https://hub.docker.com/v2/users/USERNAME" | jq
   ```

### When to Use `-`

Use `-` when:

- You've thoroughly searched and found no official DockerHub presence
- The company doesn't use Docker/containers publicly
- You've checked multiple sources and confirmed absence

## Code of Conduct

- Be respectful and professional
- Follow responsible disclosure practices
- Don't include sensitive or private information
- Respect bug bounty program rules and scope

## Questions?

If you have questions or need help:

- Open an issue on GitHub
- Check existing issues and pull requests
- Review the README for additional context

## Recognition

Contributors will be acknowledged in the repository. Thank you for helping the community! 🎉

---

**Remember**: This project is for authorized security research. Always follow ethical guidelines and legal boundaries.
