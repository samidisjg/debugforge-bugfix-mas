/**
 * User authentication system with a logic error bug.
 */

class AuthService {
    constructor() {
        this.users = [
            { id: 1, username: "admin", password: "secret123", active: true },
            { id: 2, username: "user", password: "pass456", active: true },
        ];
    }

    /**
     * Authenticate user with username and password.
     * BUG: Uses == instead of === for password comparison (type coercion vulnerability).
     */
    authenticate(username, password) {
        const user = this.users.find(u => u.username === username);
        if (!user) {
            return { success: false, message: "User not found" };
        }
        
        // BUG: Using == instead of === allows type coercion
        if (user.password == password) {
            return { success: true, user: { id: user.id, username: user.username } };
        }
        
        return { success: false, message: "Invalid password" };
    }

    /**
     * Get user by ID - BUG: doesn't check if user is active.
     */
    getUserById(id) {
        const user = this.users.find(u => u.id === id);
        if (!user) {
            return null;
        }
        return user; // Should check if active
    }

    /**
     * Create a new user.
     */
    createUser(username, password) {
        const newId = Math.max(...this.users.map(u => u.id)) + 1;
        this.users.push({ id: newId, username, password, active: true });
        return { id: newId, username };
    }
}

module.exports = AuthService;
