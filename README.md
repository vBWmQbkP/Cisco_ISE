.env示例:

# ISE Host (IP or FQDN, without https:// or port)
ISE_HOST=10.1.1.1

# ERS Admin — used to retrieve Sponsor Portal ID (port 9060)
ISE_ERS_ADMIN=admin
ISE_ERS_PASSWORD=admin

# Sponsor Account — used to create guest users
# Set in ISE: Work Centers > Guest Access > Portals & Components > Sponsor Groups
# Must enable "Access Cisco ISE guest accounts using the programmatic interface"
ISE_SPONSOR_USER=admin
ISE_SPONSOR_PASSWORD=admin

# Defaults
ISE_DEFAULT_GUEST_TYPE=Contractor (default)
ISE_DEFAULT_VALID_DAYS=30
ISE_DEFAULT_LOCATION=San Jose
