package main

import (
	"os"
	"testing"
)

func TestReadFileContent(t *testing.T) {
	// Create test file
	testFile := "test.txt"
	content := "Hello, World!"
	os.WriteFile(testFile, []byte(content), 0644)
	defer os.Remove(testFile)

	result, err := ReadFileContent(testFile)
	if err != nil {
		t.Fatalf("Expected no error, got %v", err)
	}

	if result != content {
		t.Errorf("Expected %s, got %s", content, result)
	}
}

func TestReadFileNotFound(t *testing.T) {
	_, err := ReadFileContent("nonexistent.txt")
	if err == nil {
		t.Fatal("Expected error for nonexistent file")
	}
}

func TestGetFileSize(t *testing.T) {
	// Create test file
	testFile := "size_test.txt"
	content := "Hello"
	os.WriteFile(testFile, []byte(content), 0644)
	defer os.Remove(testFile)

	size, err := GetFileSize(testFile)
	if err != nil {
		t.Fatalf("Expected no error, got %v", err)
	}

	expected := int64(len(content))
	if size != expected {
		t.Errorf("Expected size %d, got %d", expected, size)
	}
}

func TestProcessFiles(t *testing.T) {
	// Create test files
	testFiles := []string{"file1.txt", "file2.txt"}
	for _, f := range testFiles {
		os.WriteFile(f, []byte("test content"), 0644)
		defer os.Remove(f)
	}

	results, err := ProcessFiles(testFiles)
	if err != nil {
		t.Fatalf("Expected no error, got %v", err)
	}

	if len(results) != len(testFiles) {
		t.Errorf("Expected %d results, got %d", len(testFiles), len(results))
	}
}

func TestProcessFilesWithNonexistent(t *testing.T) {
	// BUG: File handle might leak when this fails
	testFiles := []string{"file1.txt", "nonexistent.txt"}
	os.WriteFile("file1.txt", []byte("test"), 0644)
	defer os.Remove("file1.txt")

	_, err := ProcessFiles(testFiles)
	if err == nil {
		t.Fatal("Expected error when file not found")
	}
}
