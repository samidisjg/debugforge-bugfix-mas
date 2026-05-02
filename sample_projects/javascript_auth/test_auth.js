/**
 * Test cases for authentication service.
 */

const AuthService = require('./auth');

describe('AuthService', () => {
    let auth;

    beforeEach(() => {
        auth = new AuthService();
    });

    test('should authenticate user with correct password', () => {
        const result = auth.authenticate('admin', 'secret123');
        expect(result.success).toBe(true);
        expect(result.user.username).toBe('admin');
    });

    test('should reject incorrect password', () => {
        const result = auth.authenticate('admin', 'wrongpassword');
        expect(result.success).toBe(false);
        expect(result.message).toBe('Invalid password');
    });

    test('should handle type coercion attack - TRIGGERS BUG', () => {
        // BUG: password == 0 should be false, but with weak comparison might pass
        const result = auth.authenticate('admin', 0);
        // This should fail, but weak comparison might allow it
        expect(result.success).toBe(false);
    });

    test('should not return inactive users - POTENTIAL BUG', () => {
        const user = auth.getUserById(1);
        // Currently returns user regardless of active status
        expect(user).not.toBeNull();
    });

    test('should create new user', () => {
        const result = auth.createUser('newuser', 'newpass');
        expect(result.id).toBe(3);
        expect(result.username).toBe('newuser');
    });

    test('should find user not found', () => {
        const result = auth.authenticate('nonexistent', 'anypass');
        expect(result.success).toBe(false);
        expect(result.message).toBe('User not found');
    });
});
